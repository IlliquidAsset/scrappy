"""Rate limiting utility for API requests"""
import time
import logging
from functools import wraps
from threading import Lock

# Set up logging
logger = logging.getLogger(__name__)

class RateLimiter:
    """Class to handle rate limiting of API requests"""
    
    def __init__(self, max_calls_per_second=1):
        """
        Initialize rate limiter
        
        Args:
            max_calls_per_second (int): Maximum number of calls per second
        """
        self.min_interval = 1.0 / max_calls_per_second
        self.last_call_time = 0
        self.lock = Lock()
    
    def wait(self):
        """
        Wait until it's appropriate to make another call
        
        Returns:
            float: Time slept in seconds
        """
        with self.lock:
            elapsed = time.time() - self.last_call_time
            to_wait = max(0, self.min_interval - elapsed)
            
            if to_wait > 0:
                logger.debug(f"Rate limiting: sleeping for {to_wait:.3f} seconds")
                time.sleep(to_wait)
            
            self.last_call_time = time.time()
            return to_wait

def rate_limited(max_per_second):
    """
    Decorator to limit the rate of function calls
    
    Args:
        max_per_second (float): Maximum calls per second
        
    Returns:
        callable: Decorated function
    """
    limiter = RateLimiter(max_per_second)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait()
            return func(*args, **kwargs)
        return wrapper
    return decorator

class GlobalRateLimiter:
    """Singleton rate limiter shared across the application"""
    
    _instance = None
    _limiters = {}
    _lock = Lock()
    
    @classmethod
    def get_instance(cls, domain, max_calls_per_second=1):
        """
        Get rate limiter instance for specific domain
        
        Args:
            domain (str): Domain to rate limit
            max_calls_per_second (float): Maximum calls per second
            
        Returns:
            RateLimiter: Rate limiter for the specified domain
        """
        with cls._lock:
            if domain not in cls._limiters:
                cls._limiters[domain] = RateLimiter(max_calls_per_second)
            return cls._limiters[domain]

def domain_rate_limited(domain, max_per_second=1):
    """
    Decorator to limit the rate of calls to a specific domain
    
    Args:
        domain (str): Domain to rate limit
        max_per_second (float): Maximum calls per second
        
    Returns:
        callable: Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the rate limiter for this domain
            limiter = GlobalRateLimiter.get_instance(domain, max_per_second)
            limiter.wait()
            return func(*args, **kwargs)
        return wrapper
    return decorator