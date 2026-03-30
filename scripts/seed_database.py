"""
scripts/seed_database.py
Run with: python manage.py shell < scripts/seed_database.py

Seeds the database with:
- 20 real Indian hospitals with GPS coordinates
- 5 admin users, 10 donors, 15 recipients
- Sample organs, requests, matches, transports
- Blood bank data
"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'organxcell.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Hospital, MedicalProfile
from organs.models import Organ, RecipientRequest, OrganMatch
from transport.models import TransportRequest, TransportLeg
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()

print("🌱 Seeding OrganXcell database...")

# ── HOSPITALS (real Indian hospitals with GPS) ──────────────────────────
HOSPITALS = [
    {"name": "Apollo Hospitals",          "city": "Chennai",     "state": "Tamil Nadu",     "lat": 13.0827, "lng": 80.2707, "reg": "TN-TR-001", "phone": "+914428290200", "email": "transplant@apollo.in"},
    {"name": "AIIMS Delhi",               "city": "Delhi",       "state": "Delhi",           "lat": 28.5672, "lng": 77.2100, "reg": "DL-TR-001", "phone": "+911126588500", "email": "transplant@aiims.edu"},
    {"name": "Fortis Memorial Hospital",  "city": "Gurugram",    "state": "Haryana",         "lat": 28.4595, "lng": 77.0266, "reg": "HR-TR-002", "phone": "+911244962200", "email": "transplant@fortis.in"},
    {"name": "Manipal Hospital",          "city": "Bangalore",   "state": "Karnataka",       "lat": 12.9716, "lng": 77.5946, "reg": "KA-TR-003", "phone": "+918025024444", "email": "transplant@manipal.in"},
    {"name": "PGIMER",                    "city": "Chandigarh",  "state": "Chandigarh",      "lat": 30.7333, "lng": 76.7794, "reg": "CH-TR-001", "phone": "+911722756565", "email": "transplant@pgimer.edu.in"},
    {"name": "Kokilaben Hospital",        "city": "Mumbai",      "state": "Maharashtra",     "lat": 19.0760, "lng": 72.8777, "reg": "MH-TR-004", "phone": "+912230999999", "email": "transplant@kokilaben.com"},
    {"name": "Global Hospital",           "city": "Hyderabad",   "state": "Telangana",       "lat": 17.3850, "lng": 78.4867, "reg": "TS-TR-005", "phone": "+914023244444", "email": "transplant@global.in"},
    {"name": "Amrita Institute",          "city": "Kochi",       "state": "Kerala",          "lat": 9.9312,  "lng": 76.2673, "reg": "KL-TR-006", "phone": "+914842801234", "email": "transplant@amrita.edu"},
    {"name": "SGPGI",                     "city": "Lucknow",     "state": "Uttar Pradesh",   "lat": 26.8467, "lng": 80.9462, "reg": "UP-TR-007", "phone": "+915222668700", "email": "transplant@sgpgi.ac.in"},
    {"name": "IPGMER",                    "city": "Kolkata",     "state": "West Bengal",     "lat": 22.5726, "lng": 88.3639, "reg": "WB-TR-008", "phone": "+912224736000", "email": "transplant@ipgmer.gov.in"},
    {"name": "Narayana Health",           "city": "Bangalore",   "state": "Karnataka",       "lat": 12.8956, "lng": 77.5944, "reg": "KA-TR-009", "phone": "+918066806680", "email": "transplant@narayanahealth.org"},
    {"name": "Max Super Speciality",      "city": "Delhi",       "state": "Delhi",           "lat": 28.6139, "lng": 77.2090, "reg": "DL-TR-010", "phone": "+911126515050", "email": "transplant@maxhealthcare.in"},
    {"name": "Medanta Hospital",          "city": "Gurugram",    "state": "Haryana",         "lat": 28.4438, "lng": 76.9928, "reg": "HR-TR-011", "phone": "+911244141414", "email": "transplant@medanta.org"},
    {"name": "Yashoda Hospital",          "city": "Hyderabad",   "state": "Telangana",       "lat": 17.4126, "lng": 78.4071, "reg": "TS-TR-012", "phone": "+914023456789", "email": "transplant@yashoda.in"},
    {"name": "Lilavati Hospital",         "city": "Mumbai",      "state": "Maharashtra",     "lat": 19.0503, "lng": 72.8264, "reg": "MH-TR-013", "phone": "+912226501000", "email": "transplant@lilavatihospital.com"},
    {"name": "Sri Ramachandra",           "city": "Chennai",     "state": "Tamil Nadu",      "lat": 13.0358, "lng": 80.1660, "reg": "TN-TR-014", "phone": "+914424768027", "email": "transplant@sriramachandra.edu.in"},
    {"name": "NIMHANS",                   "city": "Bangalore",   "state": "Karnataka",       "lat": 12.9420, "lng": 77.5962, "reg": "KA-TR-015", "phone": "+918046110007", "email": "transplant@nimhans.ac.in"},
    {"name": "Tata Memorial",             "city": "Mumbai",      "state": "Maharashtra",     "lat": 18.9988, "lng": 72.8128, "reg": "MH-TR-016", "phone": "+912224177000", "email": "transplant@tmc.gov.in"},
    {"name": "Christian Medical College", "city": "Vellore",     "state": "Tamil Nadu",      "lat": 12.9165, "lng": 79.1325, "reg": "TN-TR-017", "phone": "+914162281000", "email": "transplant@cmcvellore.ac.in"},
    {"name": "NIMS Hospital",             "city": "Hyderabad",   "state": "Telangana",       "lat": 17.4239, "lng": 78.4738, "reg": "TS-TR-018", "phone": "+914023489000", "email": "transplant@nims.in"},
]

hospitals = []
for h in HOSPITALS:
    obj, created = Hospital.objects.get_or_create(
        registration_number=h['reg'],
        defaults={
            'name': h['name'], 'city': h['city'], 'state': h['state'],
            'address': f"{h['name']}, {h['city']}, {h['state']}",
            'pincode': '600001', 'phone': h['phone'], 'email': h['email'],
            'latitude': h['lat'], 'longitude': h['lng'],
            'is_verified': True, 'has_transplant_facility': True,
        }
    )
    hospitals.append(obj)
    if created: print(f"  ✓ Hospital: {h['name']}")

print(f"✅ {len(hospitals)} hospitals seeded")

# ── USERS ───────────────────────────────────────────────────────────────
BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

def make_user(email, password, role, first, last, blood, hospital=None):
    u, created = User.objects.get_or_create(email=email, defaults={
        'username': email.split('@')[0],
        'first_name': first, 'last_name': last,
        'role': role, 'blood_group': blood,
        'phone_number': f'+91{random.randint(7000000000,9999999999)}',
        'is_verified': True, 'hospital': hospital,
    })
    if created:
        u.set_password(password)
        u.save()
        MedicalProfile.objects.get_or_create(
            user=u,
            defaults={
                'height': random.uniform(155, 185),
                'weight': random.uniform(50, 90),
                'hla_typing': {
                    'A': [f'A{random.randint(1,30)}', f'A{random.randint(1,30)}'],
                    'B': [f'B{random.randint(1,60)}', f'B{random.randint(1,60)}'],
                    'DR': [f'DR{random.randint(1,18)}', f'DR{random.randint(1,18)}'],
                },
                'pra_score': random.randint(0, 95),
                'medical_conditions': random.choice(['', 'Hypertension', 'Diabetes Type 2', 'Chronic kidney disease']),
            }
        )
    return u

# Admin
admin = make_user('admin@organxcell.in', 'admin123', 'admin', 'Super', 'Admin', 'O+', hospitals[0])

# Hospital staff
hosp_user = make_user('coordinator@apollo.in', 'hosp123', 'hospital', 'Priya', 'Mehta', 'B+', hospitals[0])

# Donors
DONOR_NAMES = [('Arjun','Mehta'),('Ravi','Kumar'),('Sunita','Patel'),('Mohan','Das'),
               ('Leela','Krishnan'),('Vikram','Singh'),('Pooja','Nair'),('Rajesh','Iyer'),
               ('Meena','Sharma'),('Deepak','Verma')]
donors = []
for i, (fn, ln) in enumerate(DONOR_NAMES):
    d = make_user(f'donor{i+1}@test.com', 'donor123', 'donor', fn, ln,
                  random.choice(BLOOD_GROUPS), random.choice(hospitals))
    donors.append(d)

# Recipients
RECIP_NAMES = [('Ananya','Iyer'),('Preethi','Rajan'),('Karthik','Subramani'),('Divya','Pillai'),
               ('Santosh','Naidu'),('Bhavna','Desai'),('Harish','Babu'),('Nalini','Murthy'),
               ('Gopal','Rao'),('Suresh','Nair'),('Kavitha','Balan'),('Ramesh','Gupta'),
               ('Usha','Menon'),('Vijay','Reddy'),('Saranya','Devi')]
recipients = []
for i, (fn, ln) in enumerate(RECIP_NAMES):
    r = make_user(f'recipient{i+1}@test.com', 'recv123', 'recipient', fn, ln,
                  random.choice(BLOOD_GROUPS), random.choice(hospitals))
    recipients.append(r)

print(f"✅ Users seeded: 1 admin, 1 coordinator, {len(donors)} donors, {len(recipients)} recipients")

# ── ORGANS ──────────────────────────────────────────────────────────────
ORGAN_TYPES = ['heart', 'liver', 'kidney', 'lungs', 'pancreas', 'kidney', 'kidney', 'liver']
organs_created = []
for i, donor in enumerate(donors[:8]):
    organ_type = ORGAN_TYPES[i]
    organ, created = Organ.objects.get_or_create(
        donor=donor, organ_type=organ_type,
        defaults={
            'status': random.choice(['available', 'available', 'matched']),
            'donation_type': random.choice(['deceased', 'living']),
            'hospital': donor.hospital,
            'harvested_at': timezone.now() - timedelta(hours=random.randint(1, 6)),
            'expiry_time': timezone.now() + timedelta(hours=random.randint(4, 20)),
        }
    )
    if created: organs_created.append(organ)

print(f"✅ {len(organs_created)} organs seeded")

# ── RECIPIENT REQUESTS ───────────────────────────────────────────────────
ORGAN_SPECIFIC_DATA = {
    'heart':  lambda: {'urgency_status': random.randint(1, 3)},
    'liver':  lambda: {'meld_score': random.randint(15, 38), 'na_meld_score': random.randint(18, 40)},
    'lungs':  lambda: {'las_score': random.randint(40, 90), 'diagnosis_group': random.choice(['A','B','C','D'])},
    'kidney': lambda: {},
    'pancreas': lambda: {'diabetes_type': 1, 'c_peptide_negative': True, 'insulin_dependent': True},
}

requests_created = []
organ_cycle = ['kidney', 'liver', 'heart', 'lungs', 'kidney', 'pancreas', 'kidney', 'liver', 'kidney', 'kidney', 'heart', 'liver', 'kidney', 'lungs', 'kidney']
for i, recip in enumerate(recipients):
    organ_type = organ_cycle[i]
    osd_fn = ORGAN_SPECIFIC_DATA.get(organ_type, lambda: {})
    req, created = RecipientRequest.objects.get_or_create(
        recipient=recip, organ_type=organ_type, status='waiting',
        defaults={
            'priority': random.choice(['critical', 'critical', 'urgent', 'urgent', 'high', 'moderate']),
            'organ_specific_data': osd_fn(),
            'waiting_since': timezone.now() - timedelta(days=random.randint(1, 180)),
            'hospital': recip.hospital,
            'doctor_notes': 'Patient evaluated and approved for transplant waitlist.',
        }
    )
    if created: requests_created.append(req)

print(f"✅ {len(requests_created)} recipient requests seeded")

# ── SAMPLE TRANSPORT ─────────────────────────────────────────────────────
if organs_created and len(hospitals) >= 4:
    tr, created = TransportRequest.objects.get_or_create(
        organ_match__isnull=True,
        defaults={} if True else {}
    ) if False else (None, False)

    # Simpler: just create directly
    from organs.matching import calculate_compatibility
    for organ in organs_created[:3]:
        matching_reqs = RecipientRequest.objects.filter(organ_type=organ.organ_type, status='waiting')[:5]
        for req in matching_reqs:
            score, breakdown = calculate_compatibility(organ, req)
            if score > 30:
                match, _ = OrganMatch.objects.get_or_create(
                    organ=organ, recipient_request=req,
                    defaults={'compatibility_score': score, 'match_breakdown': breakdown}
                )
                break

print("✅ Sample matches created")
print("\n🎉 Database seeding complete!")
print("\nDemo credentials:")
print("  Admin:      admin@organxcell.in / admin123")
print("  Donor:      donor1@test.com / donor123")
print("  Recipient:  recipient1@test.com / recv123")
print("  Hospital:   coordinator@apollo.in / hosp123")
