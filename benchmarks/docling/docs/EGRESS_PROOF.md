# Network-disabled execution proof

Execution remains blocked until Security approves a platform-specific command.
Environment variables are not an egress boundary.

Required evidence:

1. disposable non-privileged workspace path and identity;
2. absence of cloud credentials, API keys, browser state, and SSH agent;
3. OS/container firewall policy denying outbound IPv4 and IPv6, including DNS;
4. a denied control connection before the run;
5. process/network capture covering the full run;
6. a denied control connection after the run;
7. exit status, timestamps, machine profile, and reviewer signature.

Do not substitute `NO_PROXY=*`, unset proxy variables, or Docling's
`enable_remote_services=false` for an OS/container denial. Those are defense in
depth only.
