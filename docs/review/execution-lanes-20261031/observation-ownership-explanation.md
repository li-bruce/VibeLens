# Definitions and runtime invocation references

Define each observed node, field/type, source binding and lifecycle before
acceptance. Also define how runtime records identify their containing invocation.
The actual value and invocation identity are produced during execution. A file
identity alone cannot distinguish two concurrent requests about that same file.

Two different problems were previously described too loosely as missing ownership:

1. **Missing capture metadata.** Trial 06's ordinary rule/value records omitted
   their actual parent invocation. Node/field declarations and real values were
   present. This was a shared capture and verification defect. Python/Node context
   propagation now supplies actual parent-entry IDs; strict complete-run mapping
   rejects an internal record without an owner even when all responses and values
   are correct. Old failed records remain unchanged.
2. **A referenced parent lies outside the retained window.** A record has a
   parent-entry ID, but the selected/pre-start history does not contain that entry.
   This is incomplete historical evidence, not an undefined node or missing ID.
   For example, trial 10's new 153-event interval has 38 closed calls and no missing
   interval parent. Its bounded pre-start context separately lacks 195 referenced
   older parent entries. Do not describe the whole recording as complete, or say
   those observations were never defined.

A real external entry legitimately has no parent; its entry role is declared.
Missing internal metadata must fail complete acceptance. Focused/partial history
must disclose its actual missing references. Neither static edges, timestamps,
equal file IDs nor AI interpretation may supply an unwitnessed invocation.

The collector retains real open-call headers for focused capture, without reading
unselected values. This improves partial inspection; it does not rewrite history
or remove bounded retention. The human explicitly allowed truthful disclosure for
local recordings. Complete-case verification remains strict.
