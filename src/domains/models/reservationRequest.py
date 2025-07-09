class ReservationRequest :
	def __init__(self, user, platform, date, time_window, guest_count, execution_datetime) :
		self.user = user
		self.platform = platform
		self.date = date 
		self.time_window = time_window
		self.guest_count = guest_count
		self.execution_datetime = execution_datetime