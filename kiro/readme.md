https://kiro.dev/cli/
# curl -fsSL https://cli.kiro.dev/install | bash
# kiro-cli


▸ Credits: 0.01 • Time: 1s
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  !ls

  agent  inbox  outbox  Read.me
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  please read the .md file instruction in the ./agent folder.  Then process the files in the ./inbox folder.  And write
  the results and logs in the ./outbox folder.  Stop once you have process all the files in the inbox.

  I'll start by reading the instruction file in the ./agent folder, then process the files in ./inbox and write results
  to ./outbox.
● Glob "./agent/**/*.md"
  1 file
    instruction.md
● Read ./inbox

  Now let me read the instruction file:
● Read /root/kiro/./agent/instruction.md

  Now I'll read and analyze both playbooks in the inbox:
● Read (2 files)
    playbook-wo-vul-1.yaml, playbook-w-vul-1.yaml

  Now I'll analyze both playbooks and write the results to the outbox folder:
● Write /root/kiro/outbox/playbook-wo-vul-1-result.log
  added 4 lines in playbook-wo-vul-1-result.log
     1+  {
     2+    "result": "Pass",
     3+    "reason": ""
     4+  }
● Write /root/kiro/outbox/playbook-w-vul-1-result.log
  added 4 lines in playbook-w-vul-1-result.log
     1+  {
     2+    "result": "Fail",
     +    "reason": "Multiple vulnerabilities detected: (1) Hardcoded credentials found in variable definitions
     (db_password: 'SuperSecret123'). (2) Command injection risk due to unsafe use of shell with unvalidated input (rm
     -rf /home/{{ user_input }}). (3) Exposed credentials in command line (mysql password passed as plaintext argument).
     (4) Insecure file permissions on private key (mode 0644 instead of 0600)."
     4+  }

  Done. I've processed both playbooks from the inbox:

  1. playbook-wo-vul-1.yaml - Pass: Uses Ansible Vault for credentials, safe script execution, and proper file
  permissions.
  2. playbook-w-vul-1.yaml - Fail: Contains hardcoded credentials, command injection vulnerability with unvalidated
  input, exposed passwords in commands, and insecure file permissions.

  Results written to /root/kiro/outbox/.
