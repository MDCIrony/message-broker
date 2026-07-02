from abc import ABC, abstractmethod

class BaseSecurityValidator(ABC):
    @abstractmethod
    def authenticate(self, token: str) -> bool:
        """Verifies if the provided token is valid."""
        pass

    @abstractmethod
    def authorize(self, token: str, action: str, topic: str) -> bool:
        """Verifies if the token is authorized to perform action (publish/subscribe) on a topic."""
        pass

class ACLSecurityValidator(BaseSecurityValidator):
    def __init__(self):
        # In a production system, this would load from a database or secure config
        # Structure: token -> { role: str, allowed_topics: list[str], allowed_actions: list[str] }
        self._acl = {
            "admin-token-999": {
                "role": "admin",
                "allowed_actions": ["publish", "subscribe"],
                "allowed_topics": ["*"] # Wildcard for all topics
            },
            "producer-token-abc": {
                "role": "producer",
                "allowed_actions": ["publish"],
                "allowed_topics": ["*"]
            },
            "consumer-token-xyz": {
                "role": "consumer",
                "allowed_actions": ["subscribe"],
                "allowed_topics": ["noticias", "alertas", "public.*"] # Matches alerts, news or starting with public.
            }
        }

    def authenticate(self, token: str) -> bool:
        return token in self._acl

    def authorize(self, token: str, action: str, topic: str) -> bool:
        if not self.authenticate(token):
            return False
            
        rules = self._acl[token]
        
        # Check action permissions
        if action not in rules["allowed_actions"]:
            return False
            
        # Check topic permissions
        allowed_topics = rules["allowed_topics"]
        if "*" in allowed_topics:
            return True
            
        for pattern in allowed_topics:
            if pattern == topic:
                return True
            if pattern.endswith(".*") and topic.startswith(pattern[:-2]):
                return True
                
        return False

# Dependency injection instance
security_validator = ACLSecurityValidator()
