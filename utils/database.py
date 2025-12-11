<<<<<<< HEAD
"""
SQLite database for project management and tracking
"""

import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from config.settings import DATABASE_PATH
from utils.logger import setup_logger

logger = setup_logger("database")


class Database:
    """SQLite database manager for video editor projects"""
    
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database with tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Projects table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        project_id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(50),
                        video_name VARCHAR(255),
                        video_path TEXT,
                        status VARCHAR(20),
                        current_stage VARCHAR(50),
                        upload_time TIMESTAMP,
                        processing_start TIMESTAMP,
                        processing_end TIMESTAMP,
                        duration_seconds FLOAT,
                        file_size_mb FLOAT,
                        resolution VARCHAR(20),
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Pipeline stages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pipeline_stages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id VARCHAR(36),
                        stage_name VARCHAR(50),
                        status VARCHAR(20),
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        duration_seconds FLOAT,
                        tokens_used INT,
                        cost_usd DECIMAL(10,4),
                        error_message TEXT,
                        FOREIGN KEY (project_id) REFERENCES projects(project_id)
                    )
                """)
                
                conn.commit()
                logger.debug("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise
    
    def create_project(self, project_data: Dict[str, Any]) -> bool:
        """
        Create a new project entry
        
        Args:
            project_data: Dictionary with project information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO projects (
                        project_id, user_id, video_name, video_path,
                        status, current_stage, upload_time,
                        duration_seconds, file_size_mb, resolution
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_data['project_id'],
                    project_data.get('user_id', 'default'),
                    project_data['video_name'],
                    project_data['video_path'],
                    project_data.get('status', 'created'),
                    project_data.get('current_stage', 'initialized'),
                    datetime.now(),
                    project_data.get('duration_seconds'),
                    project_data.get('file_size_mb'),
                    project_data.get('resolution')
                ))
                
                conn.commit()
                logger.info(f"Created project: {project_data['project_id']}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create project: {e}", exc_info=True)
            return False
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get project: {e}", exc_info=True)
            return None
    
    def list_projects(self, user_id: Optional[str] = None, 
                     status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List projects with optional filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM projects WHERE 1=1"
                params = []
                
                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list projects: {e}", exc_info=True)
            return []
    
    def update_project_status(self, project_id: str, status: str, 
                             current_stage: str = None,
                             error_message: str = None) -> bool:
        """Update project status and stage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                updates = ["status = ?"]
                params = [status]
                
                if current_stage:
                    updates.append("current_stage = ?")
                    params.append(current_stage)
                
                if error_message:
                    updates.append("error_message = ?")
                    params.append(error_message)
                
                if status == "processing":
                    updates.append("processing_start = ?")
                    params.append(datetime.now())
                elif status in ["complete", "error", "failed"]:
                    updates.append("processing_end = ?")
                    params.append(datetime.now())
                
                params.append(project_id)
                
                query = f"UPDATE projects SET {', '.join(updates)} WHERE project_id = ?"
                cursor.execute(query, params)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update project status: {e}", exc_info=True)
            return False
    
    def log_stage(self, project_id: str, stage_name: str, status: str,
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None,
                  tokens_used: int = 0,
                  cost_usd: float = 0.0,
                  error_message: Optional[str] = None) -> bool:
        """Log pipeline stage execution"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                duration = None
                if start_time and end_time:
                    duration = (end_time - start_time).total_seconds()
                
                cursor.execute("""
                    INSERT INTO pipeline_stages (
                        project_id, stage_name, status, start_time, end_time,
                        duration_seconds, tokens_used, cost_usd, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_id, stage_name, status, start_time, end_time,
                    duration, tokens_used, cost_usd, error_message
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to log stage: {e}", exc_info=True)
            return False
    
    def get_project_stages(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all stages for a project"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM pipeline_stages 
                    WHERE project_id = ? 
                    ORDER BY start_time
                """, (project_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get stages: {e}", exc_info=True)
            return []
    
    def get_project_cost_summary(self, project_id: str) -> Dict[str, Any]:
        """Get cost summary for a project"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        SUM(tokens_used) as total_tokens,
                        SUM(cost_usd) as total_cost
                    FROM pipeline_stages
                    WHERE project_id = ?
                """, (project_id,))
                
                row = cursor.fetchone()
                
                return {
                    "total_tokens": row[0] or 0,
                    "total_cost_usd": float(row[1] or 0.0)
                }
                
        except Exception as e:
            logger.error(f"Failed to get cost summary: {e}", exc_info=True)
            return {"total_tokens": 0, "total_cost_usd": 0.0}
    
    def delete_project(self, project_id: str) -> bool:
        """Delete project and all related data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete stages first (foreign key)
                cursor.execute("DELETE FROM pipeline_stages WHERE project_id = ?", 
                             (project_id,))
                
                # Delete project
                cursor.execute("DELETE FROM projects WHERE project_id = ?", 
                             (project_id,))
                
                conn.commit()
                logger.info(f"Deleted project from database: {project_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete project: {e}", exc_info=True)
            return False
=======
"""
SQLite database for project management and tracking
"""

import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from config.settings import DATABASE_PATH
from utils.logger import setup_logger

logger = setup_logger("database")


class Database:
    """SQLite database manager for video editor projects"""
    
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database with tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Projects table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        project_id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(50),
                        video_name VARCHAR(255),
                        video_path TEXT,
                        status VARCHAR(20),
                        current_stage VARCHAR(50),
                        upload_time TIMESTAMP,
                        processing_start TIMESTAMP,
                        processing_end TIMESTAMP,
                        duration_seconds FLOAT,
                        file_size_mb FLOAT,
                        resolution VARCHAR(20),
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Pipeline stages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pipeline_stages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id VARCHAR(36),
                        stage_name VARCHAR(50),
                        status VARCHAR(20),
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        duration_seconds FLOAT,
                        tokens_used INT,
                        cost_usd DECIMAL(10,4),
                        error_message TEXT,
                        FOREIGN KEY (project_id) REFERENCES projects(project_id)
                    )
                """)
                
                conn.commit()
                logger.debug("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise
    
    def create_project(self, project_data: Dict[str, Any]) -> bool:
        """
        Create a new project entry
        
        Args:
            project_data: Dictionary with project information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO projects (
                        project_id, user_id, video_name, video_path,
                        status, current_stage, upload_time,
                        duration_seconds, file_size_mb, resolution
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_data['project_id'],
                    project_data.get('user_id', 'default'),
                    project_data['video_name'],
                    project_data['video_path'],
                    project_data.get('status', 'created'),
                    project_data.get('current_stage', 'initialized'),
                    datetime.now(),
                    project_data.get('duration_seconds'),
                    project_data.get('file_size_mb'),
                    project_data.get('resolution')
                ))
                
                conn.commit()
                logger.info(f"Created project: {project_data['project_id']}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create project: {e}", exc_info=True)
            return False
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get project: {e}", exc_info=True)
            return None
    
    def list_projects(self, user_id: Optional[str] = None, 
                     status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List projects with optional filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM projects WHERE 1=1"
                params = []
                
                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list projects: {e}", exc_info=True)
            return []
    
    def update_project_status(self, project_id: str, status: str, 
                             current_stage: str = None,
                             error_message: str = None) -> bool:
        """Update project status and stage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                updates = ["status = ?"]
                params = [status]
                
                if current_stage:
                    updates.append("current_stage = ?")
                    params.append(current_stage)
                
                if error_message:
                    updates.append("error_message = ?")
                    params.append(error_message)
                
                if status == "processing":
                    updates.append("processing_start = ?")
                    params.append(datetime.now())
                elif status in ["complete", "error", "failed"]:
                    updates.append("processing_end = ?")
                    params.append(datetime.now())
                
                params.append(project_id)
                
                query = f"UPDATE projects SET {', '.join(updates)} WHERE project_id = ?"
                cursor.execute(query, params)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update project status: {e}", exc_info=True)
            return False
    
    def log_stage(self, project_id: str, stage_name: str, status: str,
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None,
                  tokens_used: int = 0,
                  cost_usd: float = 0.0,
                  error_message: Optional[str] = None) -> bool:
        """Log pipeline stage execution"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                duration = None
                if start_time and end_time:
                    duration = (end_time - start_time).total_seconds()
                
                cursor.execute("""
                    INSERT INTO pipeline_stages (
                        project_id, stage_name, status, start_time, end_time,
                        duration_seconds, tokens_used, cost_usd, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_id, stage_name, status, start_time, end_time,
                    duration, tokens_used, cost_usd, error_message
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to log stage: {e}", exc_info=True)
            return False
    
    def get_project_stages(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all stages for a project"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM pipeline_stages 
                    WHERE project_id = ? 
                    ORDER BY start_time
                """, (project_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get stages: {e}", exc_info=True)
            return []
    
    def get_project_cost_summary(self, project_id: str) -> Dict[str, Any]:
        """Get cost summary for a project"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        SUM(tokens_used) as total_tokens,
                        SUM(cost_usd) as total_cost
                    FROM pipeline_stages
                    WHERE project_id = ?
                """, (project_id,))
                
                row = cursor.fetchone()
                
                return {
                    "total_tokens": row[0] or 0,
                    "total_cost_usd": float(row[1] or 0.0)
                }
                
        except Exception as e:
            logger.error(f"Failed to get cost summary: {e}", exc_info=True)
            return {"total_tokens": 0, "total_cost_usd": 0.0}
    
    def delete_project(self, project_id: str) -> bool:
        """Delete project and all related data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete stages first (foreign key)
                cursor.execute("DELETE FROM pipeline_stages WHERE project_id = ?", 
                             (project_id,))
                
                # Delete project
                cursor.execute("DELETE FROM projects WHERE project_id = ?", 
                             (project_id,))
                
                conn.commit()
                logger.info(f"Deleted project from database: {project_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete project: {e}", exc_info=True)
            return False
>>>>>>> d4e3c4e (update)
