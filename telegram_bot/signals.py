from django.dispatch import Signal

user_joined_to_group = Signal()
user_left_to_group = Signal()
user_start_use_bot = Signal()