# Logical enough

A small website to test student's knowledge of search expressions.

**Note:** the accounts are not password protected for simplicity. Don't use that at large scale!

To deploy on a webserver,

```bash
gunicorn --bind unix:tmp.sock -m 007 "logical_enough:create_app()"
``` 
