"""Add session columns to tables"""
from flask import current_app
from flask.cli import with_appcontext
from scrapflask.database import db
from sqlalchemy import text
import click

@click.command('add-session-columns')
@with_appcontext
def add_session_columns_command():
    """Add session-related columns to the tables."""
    try:
        # Add session_id to scraping_job table
        db.session.execute(text("""
            ALTER TABLE scraping_job
            ADD COLUMN IF NOT EXISTS session_id VARCHAR(36) UNIQUE,
            ADD COLUMN IF NOT EXISTS last_status_check TIMESTAMP;
        """))

        # Update scraping_confirmation table
        db.session.execute(text("""
            ALTER TABLE scraping_confirmation
            ADD COLUMN IF NOT EXISTS session_id VARCHAR(36),
            ADD COLUMN IF NOT EXISTS matched_name VARCHAR(255),
            ADD COLUMN IF NOT EXISTS response VARCHAR(3),
            DROP COLUMN IF EXISTS options,
            DROP COLUMN IF EXISTS expires_at,
            DROP COLUMN IF EXISTS status;
        """))

        db.session.commit()
        click.echo('Successfully added session columns')
    except Exception as e:
        click.echo(f'Error adding session columns: {e}')
        db.session.rollback()
        raise
