# Logical enough

A small website to test student's knowledge of search expressions.

Note:

```bash
gunicorn --bind unix:tmp.sock -m 007 "logical_enough:create_app()"
``` 
