import hashlib
import hmac
import structlog
from typing import Dict, Any
import httpx

from ..core.config import settings

logger = structlog.get_logger()

class SlackService:
    def __init__(self):
        self.bot_token = settings.SLACK_BOT_TOKEN
        self.signing_secret = settings.SLACK_SIGNING_SECRET
    
    async def verify_request(self, request) -> bool:
        try:
            if not self.signing_secret:
                logger.warning("Slack signing secret not configured")
                return False
            
            # Get request body
            body = await request.body()
            
            # Get timestamp and signature from headers
            timestamp = request.headers.get('X-Slack-Request-Timestamp')
            signature = request.headers.get('X-Slack-Signature')
            
            if not timestamp or not signature:
                return False
            
            # Check timestamp to prevent replay attacks (5 minute window)
            import time
            if abs(time.time() - int(timestamp)) > 300:
                return False
            
            # Create the signature base string
            sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
            
            # Calculate expected signature
            expected_signature = 'v0=' + hmac.new(
                self.signing_secret.encode('utf-8'),
                sig_basestring.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Failed to verify Slack request: {str(e)}")
            return False
    
    async def send_message(self, channel: str, message: Dict[str, Any]) -> bool:
        try:
            if not self.bot_token:
                logger.warning("Slack bot token not configured")
                return False
            
            headers = {
                'Authorization': f'Bearer {self.bot_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'channel': channel,
                **message
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://slack.com/api/chat.postMessage',
                    headers=headers,
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        logger.info(f"Message sent to Slack channel {channel}")
                        return True
                    else:
                        logger.error(f"Slack API error: {result.get('error')}")
                        return False
                else:
                    logger.error(f"Failed to send Slack message: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Slack message: {str(e)}")
            return False
    
    async def send_response(self, response_url: str, message: Dict[str, Any]) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    response_url,
                    json=message,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info("Response sent to Slack")
                    return True
                else:
                    logger.error(f"Failed to send Slack response: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Slack response: {str(e)}")
            return False
    
    async def send_incident_notification(self, channel: str, incident_data: Dict[str, Any]) -> bool:
        try:
            severity_colors = {
                'critical': '#ff0000',
                'high': '#ff9900',
                'medium': '#ffcc00',
                'low': '#36a64f'
            }
            
            color = severity_colors.get(incident_data.get('severity', 'medium'), '#36a64f')
            
            attachment = {
                "color": color,
                "title": f"Incident: {incident_data.get('title', 'Unknown')}",
                "title_link": f"https://your-platform.com/incidents/{incident_data.get('cluster_id')}",
                "fields": [
                    {
                        "title": "Severity",
                        "value": incident_data.get('severity', 'unknown'),
                        "short": True
                    },
                    {
                        "title": "Service",
                        "value": incident_data.get('service', 'unknown'),
                        "short": True
                    },
                    {
                        "title": "Status",
                        "value": incident_data.get('status', 'unknown'),
                        "short": True
                    },
                    {
                        "title": "Alert Count",
                        "value": str(incident_data.get('alert_count', 0)),
                        "short": True
                    },
                    {
                        "title": "Description",
                        "value": incident_data.get('description', 'No description available'),
                        "short": False
                    }
                ],
                "footer": "Alert Intelligence Platform",
                "ts": int(incident_data.get('created_at', 0))
            }
            
            message = {
                "text": f"Incident {incident_data.get('severity', 'medium').title()}: {incident_data.get('title', 'Unknown')}",
                "attachments": [attachment]
            }
            
            return await self.send_message(channel, message)
            
        except Exception as e:
            logger.error(f"Failed to send incident notification: {str(e)}")
            return False
    
    async def send_alert_notification(self, channel: str, alert_data: Dict[str, Any]) -> bool:
        try:
            severity_colors = {
                'critical': '#ff0000',
                'high': '#ff9900',
                'medium': '#ffcc00',
                'low': '#36a64f',
                'info': '#8e8e8e'
            }
            
            color = severity_colors.get(alert_data.get('severity', 'medium'), '#36a64f')
            
            attachment = {
                "color": color,
                "title": f"Alert: {alert_data.get('description', 'Unknown')}",
                "fields": [
                    {
                        "title": "Severity",
                        "value": alert_data.get('severity', 'unknown'),
                        "short": True
                    },
                    {
                        "title": "Service",
                        "value": alert_data.get('service', 'unknown'),
                        "short": True
                    },
                    {
                        "title": "Source",
                        "value": alert_data.get('source', 'unknown'),
                        "short": True
                    },
                    {
                        "title": "Status",
                        "value": alert_data.get('status', 'unknown'),
                        "short": True
                    }
                ],
                "footer": "Alert Intelligence Platform",
                "ts": int(alert_data.get('timestamp', 0))
            }
            
            message = {
                "text": f"Alert {alert_data.get('severity', 'medium').title()}: {alert_data.get('description', 'Unknown')}",
                "attachments": [attachment]
            }
            
            return await self.send_message(channel, message)
            
        except Exception as e:
            logger.error(f"Failed to send alert notification: {str(e)}")
            return False
    
    def format_slack_command_response(self, text: str, response_type: str = "ephemeral") -> Dict[str, Any]:
        return {
            "response_type": response_type,
            "text": text
        }
    
    def format_slack_block_response(self, blocks: list, response_type: str = "in_channel") -> Dict[str, Any]:
        return {
            "response_type": response_type,
            "blocks": blocks
        }
