"""notifications/tasks.py"""
from celery import shared_task
import logging
logger = logging.getLogger(__name__)


@shared_task
def send_match_notification(match_id):
    logger.info(f"Sending match notification for match #{match_id}")


@shared_task
def send_consent_status_notification(consent_id):
    logger.info(f"Sending consent status notification for #{consent_id}")


@shared_task
def send_transport_status_update(transport_id, status):
    logger.info(f"Transport #{transport_id} status: {status}")


@shared_task
def send_cold_chain_breach_alert(transport_id, temperature):
    logger.warning(f"COLD CHAIN BREACH: Transport #{transport_id} — {temperature}°C")


@shared_task
def send_sos_alert(organ_type, user_id):
    logger.critical(f"SOS ALERT: {organ_type} emergency from user #{user_id}")
