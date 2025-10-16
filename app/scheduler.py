# app/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from .scrape import scrape_marketplace
from .utils import logger

scheduler = BackgroundScheduler()
scheduler.add_job(scrape_marketplace, 'interval', hours=1)
scheduler.start()
logger.info("Scheduler started")
