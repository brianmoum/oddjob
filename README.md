# oddjob README

## Abstract:
A suite of individual scripts, using Selenium and other web scraping tools to perform specific operations within reservation websites on a user’s behalf, such as making advanced reservations when they are first released, keeping tabs on openings within a specified timeframe, or using AI to identify a list of potential options within a set criteria and finding availabilities within that list. 

This suite will then be hosted within GCP or another cloud computing service and accessed via text message commands so that reservation events can be made via mobile phone and executed without the need for the user to be at a computer.

## Specific Functionality:
### Restaurants:
#### Advanced Reservations:
**Use Case**: A popular restaurant that releases reservations 1-4 weeks in advance, and the day of release sees a rapid aquisition of every available seeting within seconds. It is too dificult to time the release of reservations perfectly while logging into reservation platforms manually and using the UI, and this process could be expedited, improving the odds of securing a reservation greatly, if done programattically.

**Description**: 
- Service is initiated via text message
- Service responds with prompt for initial information:
  - Name of restaurant
  - Reservation platform used by restaurant
  - Number of people
  - Date range for reservation
  - Release window for restaurant (i.e. # of days in advance that a certain day will become available to reserve)
  - Time window for booking
- Service will create an event record to attempt to book on the date of release
- On date of release, service will send reminder notification 30 mins prior to booking attempt
- Service will log into user's reservation account at the exact time of release and attempt to secure a timeslot of the selected restaurant within the desired timeframe.
- Service will send a notification if successful or unsuccessful
- If unsuccessful, service will attempt at the next release if still within the desired window. If successful, future attempts will be cancelled.
 
#### Last Minute Bookings:
**Use Case**: A gathering is organized last minute and some kind of restaurant needs to be booked within the next 0-3 days. The exact restaurant isn't important, but moreso that it fits certain criteria like the offerings available and the location. It can be a tedious process to first manually curate a list of acceptable options, sort that list by desirability, and then filter that list down to only places that have availability. All three of these tasks could be automated, significantly simplifying this task.

**Description**: 
- Service is initiated via text message
- Service responds with prompt for initial information:
  - Type of restaurant (E.g. "Bars with Dance Floors",  "Affordable Omakase", "Italian Restaurants with a Happy Hour", etc.)
  - General Location
  - Desired date range and time range
- Service sends a request to GPT or another LLM AI tool to generate a list of 20-100 options meeting the defined criteria
- For each option going down the list provided, service checks reservation options to see if there are available timeslots
- Once 10 locations have been confirmed to have availability, the service will send a notification with the list of the top 10 options, with their rank in the original list, the "best" timeslot available, and the total the number of timeslots available
- If none of the options are desirable, the user can ask for more options, at which point the service will continue the above process until 10 new options with availability are found
- The user can respond via text message to identify the listing they want to book, and the service will make the reservation on their behalf

### Tee Times:
TBD (Similar to above, but for competitive tee time reservations, e.g. Beth Page Black)

