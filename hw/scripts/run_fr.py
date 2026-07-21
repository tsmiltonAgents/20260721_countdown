"""Run freerouting with a hard timeout; usage: run_fr.py in.dsn out.ses [passes] [timeout_s]"""
import os
import subprocess
import sys

dsn, ses = sys.argv[1], sys.argv[2]
passes = sys.argv[3] if len(sys.argv) > 3 else "60"
tmo = int(sys.argv[4]) if len(sys.argv) > 4 else 240
jar = os.environ.get("FRJAR", "/private/tmp/claude-501/-Users-milton-Documents-claude-sessions-072026-20-countdown/8adcabbd-5439-4db3-9076-44dee68d56c5/scratchpad/freerouting.jar")
try:
    r = subprocess.run(["/opt/homebrew/opt/openjdk/bin/java", "-jar", jar,
                        "-de", dsn, "-do", ses, "-mp", passes],
                       capture_output=True, text=True, timeout=tmo)
    for line in r.stdout.splitlines() + r.stderr.splitlines():
        if "session completed" in line or "ERROR" in line:
            print(line)
except subprocess.TimeoutExpired:
    print(f"FR TIMEOUT after {tmo}s (SES may still have been written)")
