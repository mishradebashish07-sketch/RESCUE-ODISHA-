import urllib.parse
from sqlalchemy import create_engine, text

# Database configuration
MYSQL_USER = "root"
MYSQL_PASSWORD = urllib.parse.quote_plus("Mishra@2009")
MYSQL_HOST = "localhost"
MYSQL_PORT = "3306"
MYSQL_DB = "disaster_db"

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def setup_mysql():
    with engine.connect() as conn:
        # Create Tables with Spatial Points
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS shelters (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                location POINT NOT NULL /*!80003 SRID 4326 */,
                total_capacity INT NOT NULL,
                current_occupancy INT DEFAULT 0,
                contact_phone VARCHAR(20)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS responder_units (
                id VARCHAR(36) PRIMARY KEY,
                team_name VARCHAR(100) NOT NULL,
                team_type VARCHAR(50) NOT NULL,
                location POINT NOT NULL /*!80003 SRID 4326 */,
                is_available BOOLEAN DEFAULT TRUE
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS distress_reports (
                id VARCHAR(36) PRIMARY KEY,
                reporter_contact VARCHAR(20),
                raw_message VARCHAR(500),
                category VARCHAR(50),
                severity_score INT,
                location POINT NOT NULL /*!80003 SRID 4326 */,
                status VARCHAR(30) DEFAULT 'ASSIGNED',
                assigned_responder_id VARCHAR(36),
                nearest_shelter_id VARCHAR(36),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Clear existing data for fresh seed
        conn.execute(text("DELETE FROM shelters;"))
        conn.execute(text("DELETE FROM responder_units;"))
        conn.execute(text("DELETE FROM distress_reports;"))

        # Seed Shelters
        conn.execute(text("""
            INSERT INTO shelters (id, name, location, total_capacity, current_occupancy, contact_phone) VALUES
            (UUID(), 'Chandipur Cyclone Shelter (Baleswar)', ST_PointFromText('POINT(87.0130 21.4680)', 4326), 500, 30, '+91-678-223456'),
            (UUID(), 'Barabati Multipurpose Shelter (Cuttack)', ST_PointFromText('POINT(85.8732 20.4812)', 4326), 600, 50, '+91-671-234567'),
            (UUID(), 'Chhatrapur Relief Camp (Ganjam)', ST_PointFromText('POINT(84.9920 19.3550)', 4326), 400, 100, '+91-681-123456');
        """))

        # Seed Responders
        conn.execute(text("""
            INSERT INTO responder_units (id, team_name, team_type, location, is_available) VALUES
            (UUID(), 'ODRAF Unit 3 (Inflatable Boat Team)', 'boat_rescue', ST_PointFromText('POINT(86.9100 21.4800)', 4326), TRUE),
            (UUID(), 'ODRAF Unit 1 (Bhubaneswar Rapid Action)', 'medical_evac', ST_PointFromText('POINT(85.8200 20.2961)', 4326), TRUE);
        """))

        conn.commit()
        print("MySQL database setup and Odisha seed data inserted successfully!")

if __name__ == "__main__":
    setup_mysql()