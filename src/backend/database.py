"""
In-memory database configuration and setup for Mergington High School API
"""

from argon2 import PasswordHasher, exceptions as argon2_exceptions
from typing import Dict, Any, List, Optional


# In-memory database implementation
class InMemoryCollection:
    """Simple in-memory collection that mimics MongoDB collection interface"""
    
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}
    
    def count_documents(self, query: Dict[str, Any]) -> int:
        """Count documents matching query"""
        if not query:
            return len(self.data)
        return len([doc for doc in self.data.values() if self._matches_query(doc, query)])
    
    def insert_one(self, document: Dict[str, Any]) -> None:
        """Insert a single document"""
        doc_id = document.get('_id')
        if doc_id is None:
            raise ValueError("Document must have an _id field")
        self.data[str(doc_id)] = document.copy()
    
    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document matching query"""
        for doc in self.data.values():
            if self._matches_query(doc, query):
                return doc.copy()
        return None
    
    def find(self, query: Dict[str, Any]):
        """Find all documents matching query"""
        results = []
        for doc in self.data.values():
            if self._matches_query(doc, query):
                results.append(doc.copy())
        return results
    
    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        """Update a single document"""
        for doc_id, doc in self.data.items():
            if self._matches_query(doc, query):
                if '$push' in update:
                    for field, value in update['$push'].items():
                        if field in doc and isinstance(doc[field], list):
                            doc[field].append(value)
                elif '$set' in update:
                    for field, value in update['$set'].items():
                        doc[field] = value
                return type('UpdateResult', (), {'modified_count': 1})()
        return type('UpdateResult', (), {'modified_count': 0})()
    
    def aggregate(self, pipeline: List[Dict[str, Any]]):
        """Simple aggregation pipeline support"""
        results = []
        for stage in pipeline:
            if '$unwind' in stage:
                field = stage['$unwind'].replace('$', '')
                unwound = []
                for doc in (results if results else self.data.values()):
                    field_parts = field.split('.')
                    value = doc
                    for part in field_parts:
                        value = value.get(part, [])
                    if isinstance(value, list):
                        for item in value:
                            unwound.append({**doc, field: item})
                results = unwound
            elif '$group' in stage:
                grouped = {}
                group_by = stage['$group']['_id']
                if group_by.startswith('$'):
                    group_by = group_by.replace('$', '')
                    for doc in results:
                        field_parts = group_by.split('.')
                        value = doc
                        for part in field_parts:
                            value = value.get(part)
                        if value not in grouped:
                            grouped[value] = {'_id': value}
                results = list(grouped.values())
            elif '$sort' in stage:
                # Simple sort by _id
                results = sorted(results, key=lambda x: x.get('_id', ''))
        return results
    
    def _matches_query(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """Check if document matches query"""
        if not query:
            return True
        
        for key, value in query.items():
            if key == '_id':
                if str(doc.get('_id')) != str(value):
                    return False
            elif '.' in key:
                # Nested field query
                parts = key.split('.')
                doc_value = doc
                for part in parts:
                    if isinstance(doc_value, dict):
                        doc_value = doc_value.get(part)
                    else:
                        return False
                
                if isinstance(value, dict):
                    if '$in' in value:
                        if not isinstance(doc_value, list):
                            return False
                        if not any(item in value['$in'] for item in doc_value):
                            return False
                    elif '$gte' in value:
                        if doc_value is None:
                            return False
                        if doc_value < value['$gte']:
                            return False
                    elif '$lte' in value:
                        if doc_value is None:
                            return False
                        if doc_value > value['$lte']:
                            return False
                else:
                    if doc_value != value:
                        return False
            else:
                if key not in doc or doc[key] != value:
                    return False
        
        return True


# Create in-memory collections
activities_collection = InMemoryCollection()
teachers_collection = InMemoryCollection()

# Methods


def hash_password(password):
    """Hash password using Argon2"""
    ph = PasswordHasher()
    return ph.hash(password)


def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Verify a plain password against an Argon2 hashed password.

    Returns True when the password matches, False otherwise.
    """
    ph = PasswordHasher()
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception:
        # For any other exception (e.g., invalid hash), treat as non-match
        return False


def init_database():
    """Initialize database if empty"""

    # Initialize activities if empty
    if activities_collection.count_documents({}) == 0:
        for name, details in initial_activities.items():
            activities_collection.insert_one({"_id": name, **details})

    # Initialize teacher accounts if empty
    if teachers_collection.count_documents({}) == 0:
        for teacher in initial_teachers:
            teachers_collection.insert_one(
                {"_id": teacher["username"], **teacher})


# Initial database if empty
initial_activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Mondays and Fridays, 3:15 PM - 4:45 PM",
        "schedule_details": {
            "days": ["Monday", "Friday"],
            "start_time": "15:15",
            "end_time": "16:45"
        },
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 7:00 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "07:00",
            "end_time": "08:00"
        },
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Morning Fitness": {
        "description": "Early morning physical training and exercises",
        "schedule": "Mondays, Wednesdays, Fridays, 6:30 AM - 7:45 AM",
        "schedule_details": {
            "days": ["Monday", "Wednesday", "Friday"],
            "start_time": "06:30",
            "end_time": "07:45"
        },
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and compete in basketball tournaments",
        "schedule": "Wednesdays and Fridays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Wednesday", "Friday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore various art techniques and create masterpieces",
        "schedule": "Thursdays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Thursday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Monday", "Wednesday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and prepare for math competitions",
        "schedule": "Tuesdays, 7:15 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday"],
            "start_time": "07:15",
            "end_time": "08:00"
        },
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Friday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "amelia@mergington.edu"]
    },
    "Weekend Robotics Workshop": {
        "description": "Build and program robots in our state-of-the-art workshop",
        "schedule": "Saturdays, 10:00 AM - 2:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "10:00",
            "end_time": "14:00"
        },
        "max_participants": 15,
        "participants": ["ethan@mergington.edu", "oliver@mergington.edu"]
    },
    "Science Olympiad": {
        "description": "Weekend science competition preparation for regional and state events",
        "schedule": "Saturdays, 1:00 PM - 4:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "13:00",
            "end_time": "16:00"
        },
        "max_participants": 18,
        "participants": ["isabella@mergington.edu", "lucas@mergington.edu"]
    },
    "Sunday Chess Tournament": {
        "description": "Weekly tournament for serious chess players with rankings",
        "schedule": "Sundays, 2:00 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Sunday"],
            "start_time": "14:00",
            "end_time": "17:00"
        },
        "max_participants": 16,
        "participants": ["william@mergington.edu", "jacob@mergington.edu"]
    }
}

initial_teachers = [
    {
        "username": "mrodriguez",
        "display_name": "Ms. Rodriguez",
        "password": hash_password("art123"),
        "role": "teacher"
    },
    {
        "username": "mchen",
        "display_name": "Mr. Chen",
        "password": hash_password("chess456"),
        "role": "teacher"
    },
    {
        "username": "principal",
        "display_name": "Principal Martinez",
        "password": hash_password("admin789"),
        "role": "admin"
    }
]
