# E1XXX Details

## Message emitted:

`E1XXX: Un-Registered Error Code used.`

## Description:

This means a code snippet was calling get_error_code() with an error code that is not registered.

## Troubleshooting:

Find the error code in the traceback, and search for it in the codebase.

## Recommendation:

Add the error code to the constants.py file.