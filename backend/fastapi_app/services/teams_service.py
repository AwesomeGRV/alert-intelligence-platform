import structlog
from typing import Dict, Any
import httpx
import json

from ..core.config import settings

logger = structlog.get_logger()

class TeamsService:
    def __init__(self):
        self.webhook_url = settings.TEAMS_WEBHOOK_URL
    
    async def send_message(self, conversation_id: str, message: Dict[str, Any]) -> bool:
        try:
            if not self.webhook_url:
                logger.warning("Teams webhook URL not configured")
                return False
            
            # Format message for Teams
            teams_message = self._format_message(message)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=teams_message,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info("Message sent to Teams")
                    return True
                else:
                    logger.error(f"Failed to send Teams message: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Teams message: {str(e)}")
            return False
    
    def _format_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Convert Slack-style message to Teams format
            if 'blocks' in message:
                return self._convert_blocks_to_teams(message['blocks'])
            elif 'text' in message:
                return {
                    "text": message['text']
                }
            else:
                return {
                    "text": "Message from Alert Intelligence Platform"
                }
                
        except Exception as e:
            logger.error(f"Failed to format Teams message: {str(e)}")
            return {"text": "Error formatting message"}
    
    def _convert_blocks_to_teams(self, blocks: list) -> Dict[str, Any]:
        try:
            text_parts = []
            
            for block in blocks:
                if block.get('type') == 'header':
                    text = block.get('text', {}).get('text', '')
                    text_parts.append(f"## {text}")
                elif block.get('type') == 'section':
                    if 'text' in block:
                        text = block.get('text', {}).get('text', '')
                        text_parts.append(text)
                    if 'fields' in block:
                        for field in block['fields']:
                            field_text = field.get('text', '')
                            text_parts.append(field_text)
                elif block.get('type') == 'divider':
                    text_parts.append("---")
            
            return {
                "text": "\n\n".join(text_parts)
            }
            
        except Exception as e:
            logger.error(f"Failed to convert blocks to Teams: {str(e)}")
            return {"text": "Error converting message format"}
    
    async def send_incident_notification(self, incident_data: Dict[str, Any]) -> bool:
        try:
            severity_colors = {
                'critical': 'attention',
                'high': 'attention',
                'medium': 'accent',
                'low': 'good',
                'info': 'default'
            }
            
            theme_color = severity_colors.get(incident_data.get('severity', 'medium'), 'default')
            
            teams_message = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": self._get_theme_color(theme_color),
                "summary": f"Incident: {incident_data.get('title', 'Unknown')}",
                "sections": [
                    {
                        "activityTitle": f"Incident {incident_data.get('severity', 'medium').title()}: {incident_data.get('title', 'Unknown')}",
                        "activitySubtitle": f"Service: {incident_data.get('service', 'unknown')}",
                        "facts": [
                            {
                                "name": "Severity",
                                "value": incident_data.get('severity', 'unknown')
                            },
                            {
                                "name": "Status",
                                "value": incident_data.get('status', 'unknown')
                            },
                            {
                                "name": "Alert Count",
                                "value": str(incident_data.get('alert_count', 0))
                            },
                            {
                                "name": "Created",
                                "value": incident_data.get('created_at', 'unknown')
                            }
                        ],
                        "markdown": True
                    }
                ],
                "potentialAction": [
                    {
                        "@type": "OpenUri",
                        "name": "View Incident",
                        "targets": [
                            {
                                "os": "default",
                                "uri": f"https://your-platform.com/incidents/{incident_data.get('cluster_id')}"
                            }
                        ]
                    }
                ]
            }
            
            if incident_data.get('description'):
                teams_message["sections"][0]["text"] = incident_data['description']
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=teams_message,
                    timeout=10.0
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Failed to send Teams incident notification: {str(e)}")
            return False
    
    async def send_alert_notification(self, alert_data: Dict[str, Any]) -> bool:
        try:
            severity_colors = {
                'critical': 'attention',
                'high': 'attention',
                'medium': 'accent',
                'low': 'good',
                'info': 'default'
            }
            
            theme_color = severity_colors.get(alert_data.get('severity', 'medium'), 'default')
            
            teams_message = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": self._get_theme_color(theme_color),
                "summary": f"Alert: {alert_data.get('description', 'Unknown')}",
                "sections": [
                    {
                        "activityTitle": f"Alert {alert_data.get('severity', 'medium').title()}: {alert_data.get('description', 'Unknown')}",
                        "activitySubtitle": f"Service: {alert_data.get('service', 'unknown')}",
                        "facts": [
                            {
                                "name": "Severity",
                                "value": alert_data.get('severity', 'unknown')
                            },
                            {
                                "name": "Source",
                                "value": alert_data.get('source', 'unknown')
                            },
                            {
                                "name": "Status",
                                "value": alert_data.get('status', 'unknown')
                            },
                            {
                                "name": "Timestamp",
                                "value": alert_data.get('timestamp', 'unknown')
                            }
                        ],
                        "markdown": True
                    }
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=teams_message,
                    timeout=10.0
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Failed to send Teams alert notification: {str(e)}")
            return False
    
    def _get_theme_color(self, theme: str) -> str:
        colors = {
            'attention': 'FF0000',  # Red
            'accent': 'FFCC00',     # Yellow
            'good': '36A64F',       # Green
            'default': '8E8E8E'     # Gray
        }
        return colors.get(theme, '8E8E8E')
    
    def format_teams_command_response(self, text: str) -> Dict[str, Any]:
        return {
            "type": "message",
            "text": text
        }
    
    def format_teams_card_response(self, title: str, facts: list, actions: list = None) -> Dict[str, Any]:
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": title,
            "sections": [
                {
                    "activityTitle": title,
                    "facts": facts,
                    "markdown": True
                }
            ]
        }
        
        if actions:
            card["potentialAction"] = actions
        
        return card
