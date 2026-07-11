"""
Session Store - In-memory storage for active profile and chat history.
Manages user sessions without requiring a database.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime

class SessionStore:
    """In-memory session storage for active profiles and chat history"""
    
    def __init__(self):
        # Store active profile data: {session_id: profile_data}
        self._active_profiles: Dict[str, Dict[str, Any]] = {}
        
        # Store chat history: {session_id: [messages]}
        self._chat_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def set_active_profile(self, session_id: str, profile_data: Dict[str, Any]) -> None:
        """
        Set the active profile for a session.
        
        Args:
            session_id: Unique session identifier (typically profile_id)
            profile_data: Full profile data from JSON
        """
        self._active_profiles[session_id] = profile_data
        
        # Initialize chat history if not exists
        if session_id not in self._chat_history:
            self._chat_history[session_id] = []
    
    def get_active_profile(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the active profile for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Profile data or None if no active session
        """
        return self._active_profiles.get(session_id)
    
    def get_profile_by_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Get profile by its profile_id (alias for get_active_profile).
        
        Args:
            profile_id: Unique profile identifier
            
        Returns:
            Profile data or None if no active session
        """
        return self.get_active_profile(profile_id)
    
    def add_chat_message(self, session_id: str, role: str, content: str, **metadata: Any) -> None:
        """
        Add a message to chat history.
        
        Args:
            session_id: Unique session identifier
            role: Message role (user/assistant/system)
            content: Message content
        """
        if session_id not in self._chat_history:
            self._chat_history[session_id] = []
        
        self._chat_history[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **metadata,
        })
    
    def get_chat_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get chat history for a session.
        
        Args:
            session_id: Unique session identifier
            limit: Optional limit on number of messages to return
            
        Returns:
            List of chat messages
        """
        history = self._chat_history.get(session_id, [])
        
        if limit:
            return history[-limit:]
        
        return history
    
    def clear_chat_history(self, session_id: str) -> None:
        """Clear chat history for a session"""
        if session_id in self._chat_history:
            self._chat_history[session_id] = []
    
    def clear_session(self, session_id: str) -> None:
        """Clear all data for a session"""
        self._active_profiles.pop(session_id, None)
        self._chat_history.pop(session_id, None)
    
    def get_all_sessions(self) -> List[str]:
        """Get list of all active session IDs"""
        return list(self._active_profiles.keys())
    
    # Convenience methods for simplified access (used by tools)
    def set_profile(self, profile_data: Dict[str, Any]) -> None:
        """
        Set active profile using profile_id from the data itself.
        Convenience wrapper for single-profile workflows.
        
        Args:
            profile_data: Profile data (must contain 'profile_id')
        """
        profile_id = profile_data.get('profile_id')
        if not profile_id:
            raise ValueError("Profile data must contain 'profile_id'")
        self.set_active_profile(profile_id, profile_data)
    
    def get_profile(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recently set active profile.
        Convenience method for single-profile workflows.
        
        Returns:
            Profile data or None if no profiles are active
        """
        if not self._active_profiles:
            return None
        # Return the most recently added profile
        # (In real app with multiple sessions, you'd track current session differently)
        return list(self._active_profiles.values())[-1]


# Global session store instance
session_store = SessionStore()
