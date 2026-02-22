# timetracker

A custom time tracker

Personal project to track time spent on various tasks and projects.

I developed a Python-based CLI tool to automate the granular tracking of my creative and technical workflows. The application functions as a background service that intelligently scrapes active window titles at high-frequency intervals to categorize real-time activity. To provide actionable insights, I engineered a data-processing layer that aggregates this raw data every 15 minutes, pushing a summarized 'time-spent' report to a calendar API via a custom integration. This project replaced manual logging with an automated, data-driven system, allowing me to audit my productivity and balance project milestones with surgical precision."

## Installation

Dependencies: requires Python 3.x and the `icalendar` library:

$pip3 install ics

## Features

- Own your own data: Track your activities either in a calendar app using .ics or in a .cvs file.
- Terminal execution and open source code.
- 15 minute time blocks
- .cvs log file in main directory
- Local host web server to view logs in a calendar format- allows a subscription.

## How to Use

Install the dependencies and clone the repo.

Run ./main.sh in your terminal.
Cancel the running process with Ctrl+C.

Use the

## Future features

- Color code ical events based on task/project productivity.
- Compile executable and run on startup.
