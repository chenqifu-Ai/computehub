"""
Celery Configuration for ComputeHub
"""

# Broker settings (Redis)
broker_url = 'redis://localhost:6379/0'

# Result backend settings
result_backend = 'redis://localhost:6379/0'

# Task settings
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Task execution settings
task_track_started = True
task_time_limit = 3600  # 1 hour max
task_soft_time_limit = 3300  # 55 minutes

# Retry settings
task_acks_late = True
task_reject_on_worker_lost = True
task_default_retry_delay = 60  # 1 minute
task_max_retries = 3

# Concurrency (adjust based on CPU cores)
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000

# Monitoring
worker_send_task_events = True
task_send_sent_event = True
