# Kodi-Email-Timer
Python script to add kodi pvr timers based on email content.

This project was created as an excercise getting familiar with email handling in Python along with my other project KODI-Email-Alert.

The purpose was to automatically read an email and add a kodi pvr timer entry based on information contained in the email body.
The script leverages Python's imaplib to log into an imap server, using server hostname and user credentials provided in an configuration file. 

The primary trigger for an email to be processed is the subject line, which is configurable as well as the list of allowed senders which is checked on receive. If the subject line matches the configured value the mail body is searched for signal words to identify what title is to be recorded, when and on what channel. These signal words must also be specified in the configuration file.

The script retrieves the EPG data (broadcast list) from kodi for the specified channel. If a match is found for the requested title a pvr timer entry is created and added to kodi's pvr timer list. If no particular start time is specified, timer entries are created for every match in the EPG data base. The (then updated) kodi pvr timer list is (optionally) replied to the sender for confirmation.

If no signal words are found or provided in the email body the script can reply to the sender with the currently configured kodi pvr timer list. This can also be used for help or info as the signal words are supplied in the headline of the replied timer list. It requires the reply subject and info text to be configured. 

Since the script excessively uses kodi JSON-RPC calls to retrieve information from kodi and eventually add the pvr timer the kodi host must be online. The script tries to wake up the kodi host via wake-on-lan command if the host is not responsive prior to sending the JSON-RPC requests. To that purpose, the kodi host's mac address should be specified in the configuration.
