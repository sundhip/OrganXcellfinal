"""
organs/matching.py — OrganXcell Matching Engine
================================================
Organ-specific compatibility algorithms:
  kidney   : HLA-based (zero-mismatch bonus), PRA, NOTTO geo
  liver    : MELD → Na-MELD → PELD (paediatric)
  heart    : 4-tier urgency (1A/1B/2/Other), geo 20pts
  lungs    : LAS-inspired, diagnosis group, height-based size
  pancreas : diabetes-type-aware, DR-locus HLA, BMI delta
  default  : ABO + wait + geo fallback
"""
from __future__ import annotations
from typing import Tuple, Dict


def calculate_compatibility(organ, recipient_request) -> Tuple[float, Dict]:
    donor     = organ.donor
    recipient = recipient_request.recipient

    # ── 1. ABO blood-group compatibility (hard filter) ──────────
    if not _abo_compatible(donor.blood_group, recipient.blood_group):
        return 0.0, {'abo': 'incompatible'}

    osd_organ = organ.organ_specific_data or {}
    osd_recip = recipient_request.organ_specific_data or {}
    r_profile = getattr(recipient, 'medical_profile', None)
    d_profile = getattr(donor,     'medical_profile', None)

    organ_type = organ.organ_type.lower()
    dispatch = {
        'kidney':   _kidney,
        'liver':    _liver,
        'heart':    _heart,
        'lungs':    _lungs,
        'pancreas': _pancreas,
    }
    fn = dispatch.get(organ_type, _default)
    score, breakdown = fn(donor, recipient, organ, recipient_request, d_profile, r_profile, osd_organ, osd_recip)

    # Geo modifier (all organs)
    geo_score, geo_tier = _geo_score(organ, recipient_request)
    score += geo_score
    breakdown['geographic'] = {'tier': geo_tier, 'points': geo_score}

    # Clamp
    score = min(max(round(score, 2), 0), 100)
    return score, breakdown


# ── ABO compatibility ────────────────────────────────────────────────────
COMPATIBLE = {'O': ['O','A','B','AB'], 'A': ['A','AB'], 'B': ['B','AB'], 'AB': ['AB']}

def _abo_compatible(donor_bg: str, recipient_bg: str) -> bool:
    d = donor_bg.replace('+','').replace('-','').upper()
    r = recipient_bg.replace('+','').replace('-','').upper()
    return r in COMPATIBLE.get(d, [])


# ── Geographic scoring — NOTTO zone tiers ────────────────────────────────
def _geo_score(organ, req) -> Tuple[float, str]:
    oh = getattr(organ, 'hospital', None) or getattr(organ.donor, 'hospital', None)
    rh = req.hospital
    if not oh or not rh:
        return 5, 'unknown'
    if oh.pk == rh.pk:
        return 20, 'same_hospital'
    if oh.city.lower() == rh.city.lower():
        return 15, 'same_city'
    if oh.state.lower() == rh.state.lower():
        return 10, 'same_state'
    if _same_notto_zone(oh.state, rh.state):
        return 7, 'same_zone'
    return 3, 'cross_zone'


NOTTO_ZONES = {
    'North':  ['Delhi','Haryana','Himachal Pradesh','Jammu and Kashmir','Punjab','Rajasthan','Uttar Pradesh','Uttarakhand','Chandigarh'],
    'South':  ['Andhra Pradesh','Goa','Karnataka','Kerala','Puducherry','Tamil Nadu','Telangana','Lakshadweep'],
    'East':   ['Bihar','Chhattisgarh','Jharkhand','Odisha','Sikkim','West Bengal','Andaman and Nicobar Islands'],
    'West':   ['Dadra and Nagar Haveli','Daman and Diu','Gujarat','Madhya Pradesh','Maharashtra'],
    'NE':     ['Arunachal Pradesh','Assam','Manipur','Meghalaya','Mizoram','Nagaland','Tripura'],
}

def _same_notto_zone(s1: str, s2: str) -> bool:
    for states in NOTTO_ZONES.values():
        if s1 in states and s2 in states:
            return True
    return False


# ── HLA scoring ─────────────────────────────────────────────────────────
def _hla_score(d_profile, r_profile, max_pts=35, zero_bonus=5) -> Tuple[float, int]:
    if not d_profile or not r_profile:
        return max_pts * 0.5, -1
    d_hla = d_profile.hla_typing or {}
    r_hla = r_profile.hla_typing or {}
    mismatches = 0
    for locus in ['A', 'B', 'DR']:
        d_alleles = set(d_hla.get(locus, []))
        r_alleles = set(r_hla.get(locus, []))
        mismatches += len(d_alleles.symmetric_difference(r_alleles)) // 2
    if mismatches == 0:
        return max_pts + zero_bonus, 0
    deduction = min(mismatches * 5, max_pts)
    return max(0, max_pts - deduction), mismatches


# ── Wait-time score (linear, capped at max) ──────────────────────────────
def _wait_score(waiting_since, max_pts=25) -> float:
    from django.utils import timezone
    days = (timezone.now() - waiting_since).days
    return min(max_pts, (days / 180) * max_pts)


# ── Age delta score ──────────────────────────────────────────────────────
def _age_score(donor, recipient, max_pts=10) -> float:
    from datetime import date
    try:
        dd = donor.date_of_birth or date(1970,1,1)
        rd = recipient.date_of_birth or date(1970,1,1)
        delta = abs((dd - rd).days) / 365
        return max(0, max_pts - (delta / 10) * max_pts)
    except Exception:
        return max_pts * 0.5


# ═════════════════════════════════════════════════════════════════════════
# ORGAN-SPECIFIC ALGORITHMS
# ═════════════════════════════════════════════════════════════════════════

def _kidney(donor, recipient, organ, req, d_profile, r_profile, osd_o, osd_r):
    hla_s, mismatches = _hla_score(d_profile, r_profile, max_pts=35, zero_bonus=5)
    pra = getattr(r_profile, 'pra_score', 0) or 0
    pra_s = max(0, 25 - (pra / 100) * 15)  # high PRA = harder to match
    wait_s = _wait_score(req.waiting_since, 25)
    age_s  = _age_score(donor, recipient, 5)
    score  = hla_s + pra_s + wait_s + age_s
    return score, {
        'hla': {'points': hla_s, 'mismatches': mismatches},
        'pra': {'points': pra_s, 'pra_value': pra},
        'wait_time': {'points': wait_s},
        'age_delta': {'points': age_s},
    }


def _liver(donor, recipient, organ, req, d_profile, r_profile, osd_o, osd_r):
    # MELD / Na-MELD / PELD urgency
    meld    = osd_r.get('meld_score', 15)
    na_meld = osd_r.get('na_meld_score', meld)
    peld    = osd_r.get('peld_score')  # paediatric (<12)
    urgency_s = min(55, (na_meld / 40) * 55) if not peld else min(55, (peld / 30) * 55)
    size_s    = 16  # simplified; real: donor/recipient body size comparison
    wait_s    = _wait_score(req.waiting_since, 10)
    score     = urgency_s + size_s + wait_s
    return score, {
        'meld_urgency': {'points': urgency_s, 'meld': meld, 'na_meld': na_meld},
        'body_size':    {'points': size_s},
        'wait_time':    {'points': wait_s},
    }


def _heart(donor, recipient, organ, req, d_profile, r_profile, osd_o, osd_r):
    urgency_map = {1: 45, 2: 35, 3: 20, 4: 10}
    urg_level   = osd_r.get('urgency_status', 2)
    urg_s       = urgency_map.get(urg_level, 20)
    size_s      = 22  # simplified height/weight matching
    age_s       = _age_score(donor, recipient, 10)
    score       = urg_s + size_s + age_s
    return score, {
        'urgency_1A_1B': {'points': urg_s, 'level': urg_level},
        'body_size':     {'points': size_s},
        'age_delta':     {'points': age_s},
    }


def _lungs(donor, recipient, organ, req, d_profile, r_profile, osd_o, osd_r):
    las    = osd_r.get('las_score', 50)
    las_s  = min(40, (las / 100) * 40)
    diag   = osd_r.get('diagnosis_group', 'B')
    diag_s = {'A': 20, 'B': 15, 'C': 10, 'D': 8}.get(diag, 12)
    height_s = 16  # simplified height matching
    age_s    = _age_score(donor, recipient, 5)
    score    = las_s + diag_s + height_s + age_s
    return score, {
        'las_score':   {'points': las_s, 'las': las},
        'diagnosis':   {'points': diag_s, 'group': diag},
        'height_match':{'points': height_s},
        'age_delta':   {'points': age_s},
    }


def _pancreas(donor, recipient, organ, req, d_profile, r_profile, osd_o, osd_r):
    # T1 diabetes + C-peptide negative = highest priority
    diab_type   = osd_r.get('diabetes_type', 1)
    cpep_neg    = osd_r.get('c_peptide_negative', False)
    diab_s      = 25 if (diab_type == 1 and cpep_neg) else 12
    hla_s, mm   = _hla_score(d_profile, r_profile, max_pts=25)
    # BMI match
    bmi_s       = 20  # simplified
    wait_s      = _wait_score(req.waiting_since, 10)
    age_s       = _age_score(donor, recipient, 5)
    score       = diab_s + hla_s + bmi_s + wait_s + age_s
    return score, {
        'diabetes_type': {'points': diab_s, 'type': diab_type, 'c_peptide_neg': cpep_neg},
        'hla_dr':        {'points': hla_s, 'mismatches': mm},
        'bmi_match':     {'points': bmi_s},
        'wait_time':     {'points': wait_s},
        'age_delta':     {'points': age_s},
    }


def _default(donor, recipient, organ, req, d_profile, r_profile, osd_o, osd_r):
    wait_s = _wait_score(req.waiting_since, 50)
    age_s  = _age_score(donor, recipient, 10)
    score  = wait_s + age_s + 20  # base ABO compatible points
    return score, {'wait_time': {'points': wait_s}, 'age_delta': {'points': age_s}}
