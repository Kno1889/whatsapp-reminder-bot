# whatsapp-automation

Desired flow of operations: 
- Download 3 daily files
- send to main gc
- success -> send confirmation msg to test gc
- error -> raise it and try to get error info in test gc. Errors I can handle: 
    - file not found
    - Unable to send any of the 3 msgs -> retry? 

Documenting difficulties faced: 
- finding a whatsapp API. Third API worked
- Finding right platform to launch. Considered PythonAnywhere, Replit
- Timing. Milliseconds discrepancy. Small bugfix
- Exception handling

Difficulties faced on drone project: 
- issues with connecting FC to Mac, then computer
- Issues flashing firmware
- Fear (?) of soldering -> procrastination

# V2.0, the relaunch
This is a bot that will fetch 

Starting over. Steps:
- gdrive media fetcher 
- whatsapp sending component
- automate
- skip the google drive component