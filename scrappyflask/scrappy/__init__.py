"""
Scrappy - Property Data Scraping Module
"""
from scrappy.scrapers.property_scraper import scrape_property_data
from scrappy.scrapers.detail_scraper import scrape_details

__version__ = "1.0.0"
__all__ = ['scrape_property_data', 'scrape_details']