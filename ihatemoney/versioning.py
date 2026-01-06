from flask import g
from sqlalchemy.orm.attributes import get_history
from sqlalchemy_continuum import VersioningManager
from sqlalchemy_continuum.plugins.flask import fetch_remote_addr

from ihatemoney.utils import FormEnum


class LoggingMode(FormEnum):
    

    DISABLED = 0
    ENABLED = 1
    RECORD_IP = 2

    @classmethod
    def default(cls):
        return cls.ENABLED


class ConditionalVersioningManager(VersioningManager):
    

    def __init__(self, tracking_predicate, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.tracking_predicate = tracking_predicate

    def before_flush(self, session, flush_context, instances):
        if self.tracking_predicate():
            return super().before_flush(session, flush_context, instances)
        else:
            
            
            
            self.unit_of_work(session)

    def after_flush(self, session, flush_context):
        if self.tracking_predicate():
            return super().after_flush(session, flush_context)
        else:
            
            
            
            self.unit_of_work(session)


def version_privacy_predicate():
    
    logging_enabled = False
    try:
        if g.project.logging_preference != LoggingMode.DISABLED:
            logging_enabled = True

        
        
        old_logging_mode = get_history(g.project, "logging_preference")[2]
        if old_logging_mode and old_logging_mode[0] != LoggingMode.DISABLED:
            logging_enabled = True
    except AttributeError:
        
        
        if LoggingMode.default() != LoggingMode.DISABLED:
            logging_enabled = True
    return logging_enabled


def get_ip_if_allowed():
    
    ip_logging_allowed = False
    try:
        if g.project.logging_preference == LoggingMode.RECORD_IP:
            ip_logging_allowed = True

        
        
        old_logging_mode = get_history(g.project, "logging_preference")[2]
        if old_logging_mode and old_logging_mode[0] == LoggingMode.RECORD_IP:
            ip_logging_allowed = True
    except AttributeError:
        
        
        if LoggingMode.default() == LoggingMode.RECORD_IP:
            ip_logging_allowed = True

    if ip_logging_allowed:
        return fetch_remote_addr()
    else:
        return None
