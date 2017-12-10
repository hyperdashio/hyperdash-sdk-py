"""This file contains functionality for parsing logs and taking actions upon them"""

import re

class LogParser:
    def __init__(self, hd_client):
        self._hd_client = hd_client
        self._regexes = self._get_regexes()
        self._token_buf = []

    def handle_token(self, token):
        """Handles a new token as part of the ongoing stream.
        
        Accepts a token and determines if this token combined with previous
        tokens constitutes a line, and if so, it applies the known regexes
        and if there's a match emits the associated metrics.
        """
        self._token_buf.append(token)
        if "\n" in token:
            line = b"".join(self._token_buf)
            self._handle_line(line)
            self._token_buf = []
    
    def _handle_line(self, line):
        for regex in self._regexes:
            result = regex.search(line)
            if result:
                num = float(result.group(1))
                self._hd_client.metric("test", num, log=False)

    def _get_regexes(self):
        """Get regexes returns a list of regular expressions that should be applied to each line."""
        regexes = ["he([0-9.]+)llo"]
        return [re.compile(x) for x in regexes]
