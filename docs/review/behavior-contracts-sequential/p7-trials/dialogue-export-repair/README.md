# Public dialogue export

The actual Node trial export treated the desktop-injected AGENTS/environment
message as a user's answer. It also dropped an entire message starting with an
environment block even when a real request followed it.

The exporter now excludes only a complete host setup message. Ordinary
discussion of AGENTS files and requests following environment metadata remain.
Reasoning and arbitrary tool output retain their existing exclusion rules.

`first.log` preserves the two new failing cases. The repaired exporter passed
12 focused tests. Re-exporting the same unchanged Node session removed exactly
one host-only message: all 112 actual dialogue records and all usage samples
remain byte-equivalent after parsing. `results.json` records the source hash.
The provisional exports stay in the local validation directory until the final
native trials finish. No Skill installation, runtime or application file changed.
