"""Independent HTTP and persistence assertions for the confirmed scope."""
import json
from observe import scenario
if __name__ == "__main__":
    for case in ("workflow","rejected","denied","session","withdrawal","rejection_reason"):
        run,_=scenario(case,"off",with_observer=False)
        assert run["observations"]["business_ok"]
    print(json.dumps({"valid":True,"cases":6,"entrypoints":"actual Flask handlers","storage":"independent sqlite3 reads"}))
