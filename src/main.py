import subprocess
import asyncio
import time
import csv
from datetime import datetime, timedelta
import os
from ics import Calendar, Event
import http.server
import socketserver
import threading

dictionary = {}
# The URL for your local calendar server. You will subscribe to this URL.
# If you later host the file on a public server, you would change this URL.
ICS_CALENDAR_URL = "http://127.0.0.1:8000/time_audit.ics"

def format_time(seconds):
    """
    Converts a time in seconds to a human-readable string in minutes or seconds.
    """
    if seconds >= 60:
        minutes = seconds / 60.0
        return f"{minutes:.2f} minutes"
    else:
        return f"{seconds} seconds"

class IcsHandler(http.server.SimpleHTTPRequestHandler):
    """A custom handler that only serves the .ics file and nothing else."""
    def do_GET(self):
        if self.path == '/time_audit.ics':
            self.path = 'time_audit.ics'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')

def run_server():
    """Starts a simple HTTP server in a new thread to serve the .ics file."""
    PORT = 8000
    with socketserver.TCPServer(("", PORT), IcsHandler) as httpd:
        print(f"Serving time_audit.ics at {ICS_CALENDAR_URL}")
        httpd.serve_forever()

async def main():
    """Starts the main application loop, running data recording, summarization, and the server concurrently."""
    # Start the HTTP server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Run the existing data collection tasks
    await asyncio.gather(record_seconds(), summarize_data())

async def record_seconds():
    """Continuously monitors and records active application and window titles every second."""
    while True:
        app = get_active_application_name()
        title = get_active_window_title_mac()
        
        if app is None or title is None:
            print("Could not retrieve active application or window title.")
            await asyncio.sleep(1)
            continue

        count_window_titles(app, title, dictionary)
        await asyncio.sleep(1)

async def summarize_data():
    """
    Waits for the next 15-minute mark, then writes data to a CSV and prints a summary.
    This function will be called every 15 minutes.
    """
    while True:
        now = datetime.now()
        current_minute = now.minute
        
        # Calculate time to wait until the next 15-minute mark
        minutes_to_wait = 15 - (current_minute % 15)
        seconds_to_wait = (minutes_to_wait * 60) - now.second
        
        if seconds_to_wait < 0:
            seconds_to_wait += 900 # Add 15 minutes (900 seconds) if we've already passed the mark
            
        print(f"Waiting for {minutes_to_wait} minutes until the next 15-minute interval...")
        await asyncio.sleep(seconds_to_wait)
        
        # Once the wait is over, get the timestamp and write to the CSV
        # The timestamp now reflects the start of the 15-minute block that just finished
        timestamp = (datetime.now() - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M")
        
        # Check if any activity was recorded in the last 15 minutes
        if not dictionary:
            activity_summary_string = "No activity recorded"
            ics_event_title = "Idle"
        else:
            # Create a list of all activity items to sort
            all_activity = []
            for app, titles in dictionary.items():
                if isinstance(titles, dict):
                    for title, count in titles.items():
                        all_activity.append({'app': app, 'title': title, 'count': count})
                else:
                    all_activity.append({'app': app, 'title': "No title recorded", 'count': titles})
            
            # Sort the activity list by count in descending order
            sorted_activity = sorted(all_activity, key=lambda item: item['count'], reverse=True)
            
            # Construct the summary string from the sorted list
            summary_list = []
            for item in sorted_activity:
                summary_list.append(f"{item['app']} - {item['title']} - {format_time(item['count'])}")
            activity_summary_string = "\n".join(summary_list)
            
            # Get the most active item for the ICS title
            most_active_item = sorted_activity[0]
            app = most_active_item['app']
            title = most_active_item['title']
            
            # Format the title to be concise
            full_title = f"{title} - {app}"
            if len(full_title) > 32:
                ics_event_title = full_title[:30] + "..."
            else:
                ics_event_title = full_title

        print(f"--- Writing data to CSV at {timestamp} ---")
        write_to_csv(timestamp, activity_summary_string)
        print("--- CSV file updated ---")
        
        print(f"--- Writing data to ICS at {timestamp} ---")
        write_to_ics(timestamp, activity_summary_string, ics_event_title)
        print("--- ICS file updated ---")
        
        # You can optionally print a summary to the console as well
        print("\n--- Summary of the last 15 minutes ---")
        summarize_dictionary(dictionary)
        print("--------------------------------------")
        
        # Clear the dictionary for the next 15-minute block
        dictionary.clear()
        
def write_to_csv(timestamp, activity_summary_string):
    """
    Formats and appends the dictionary data to a CSV file.
    Each row includes a timestamp and a summary of all activity in that time block.
    """
    filename = "activity_log.csv"
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'activity_summary']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            'timestamp': timestamp,
            'activity_summary': activity_summary_string
        })

def write_to_ics(timestamp, activity_summary_string, event_title):
    """
    Writes a new calendar event to an .ics file with the activity summary.
    The file can be uploaded to a public server to create a shareable URL.
    """
    # Only write an event if there was activity recorded
    if activity_summary_string == "No activity recorded":
        return

    filename = "time_audit.ics"
    
    if os.path.exists(filename):
        with open(filename, 'r') as icsfile:
            c = Calendar(icsfile.read())
    else:
        c = Calendar(creator='-///Time Audit')

    e = Event()
    e.name = event_title
    e.begin = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
    e.duration = {'minutes': 15}
    e.description = activity_summary_string
    e.url = ICS_CALENDAR_URL
    
    c.events.add(e)
    
    with open(filename, 'w') as icsfile:
        icsfile.writelines(c)


def summarize_dictionary(dictionary):
    """Calculates and prints the top 3 applications by total usage time, with title details."""
    summary = {}
    for app, titles in dictionary.items():
        if isinstance(titles, dict):
            total_time = sum(titles.values())
            summary[app] = total_time
    
    sorted_summary = sorted(summary.items(), key=lambda item: item[1], reverse=True)
    
    top_three = sorted_summary[:3]
    for app, total_time in top_three:
        print(f"App: {app}, Total Time: {format_time(total_time)}")
        
        if app in dictionary and isinstance(dictionary[app], dict):
            sorted_titles = sorted(dictionary[app].items(), key=lambda item: item[1], reverse=True)
            for title, time_in_seconds in sorted_titles:
                print(f"  - Title: {title}, Time: {format_time(time_in_seconds)}")

def count_window_titles(app, title, dictionary):
    """Increments the counter for a given app and window title."""
    array = list(set(title.split(" - ")))
    if app in array:
        array.remove(app)
        
    remove_list = ["Audio playing", "Jeffrey"]
    for word in remove_list:
        if word in array:
            array.remove(word)
    array.sort()
    
    combined_string = " - ".join(array)
    
    if app is None:
        return

    if app not in dictionary:
        dictionary[app] = {}
        
    if combined_string not in dictionary[app]:
        dictionary[app][combined_string] = 0
        
    dictionary[app][combined_string] += 1

def get_active_window_title_mac():
    """Retrieves the title of the currently active window in macOS."""
    try:
        script = 'tell application "System Events" to tell (first process whose frontmost is true) to return name of window 1'
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, IndexError):
        return None

def get_active_application_name():
    """Retrieves the name of the currently active application in macOS."""
    applescript_code = """
    tell application "System Events"
        set active_app_name to name of first application process whose frontmost is true
    end tell
    return active_app_name
    """
    try:
        process = subprocess.run(
            ['osascript', '-e', applescript_code],
            capture_output=True,
            text=True,
            check=True
        )
        return process.stdout.strip()
    except subprocess.CalledProcessError:
        return None

if __name__ == "__main__":
    asyncio.run(main())

