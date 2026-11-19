---- MODULE Model ----
EXTENDS Naturals
VARIABLES grant, archive
vars == <<grant, archive>>
Init == grant = 0 /\ archive = 0
Share == grant = 0 /\ grant' = 1 /\ UNCHANGED archive
Revoke == grant = 1 /\ grant' = 0 /\ UNCHANGED archive
Archive == archive = 0 /\ archive' = 1 /\ UNCHANGED grant
Restore == archive = 1 /\ archive' = 0 /\ UNCHANGED grant
Next == Share \/ Revoke \/ Archive \/ Restore
Spec == Init /\ [][Next]_vars
TypeInvariant == grant \in 0..1 /\ archive \in 0..1
====
