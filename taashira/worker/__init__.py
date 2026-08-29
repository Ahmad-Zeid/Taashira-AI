"""Background execution. Runs agents; never serves the browser.

This is the half of the system that makes the project a Taskmaster entry rather than
a chatbot: it wakes on a schedule with no human present, re-evaluates every active
campaign, and acts only when something actually changed.
"""
