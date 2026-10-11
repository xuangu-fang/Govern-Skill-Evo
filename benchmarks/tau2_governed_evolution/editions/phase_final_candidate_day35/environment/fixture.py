"""Build the exact final-candidate Airline DB without deferred or rejected fixtures."""

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.joint_settlement_destination_scope.environment.fixture import (
    build_core_db,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.data_model import (
    FinalCandidateAirlineDB,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.fixture import (
    build_gate0_db,
)

from .control_fixture import add_airline_controls


P4_USERS = {
    "cameron_lane_5101", "devon_price_5202", "ellis_morgan_5303", "frankie_ross_5404",
    "hayden_brooks_5505", "jordan_ellis_5606", "kendall_shaw_5707", "logan_mills_5808",
}
CARDINALITY_USERS = {
    "fc_air_aurora", "fc_air_beacon", "fc_air_comet", "fc_air_delta",
    "fc_air_ember", "fc_air_fjord", "fc_air_glade", "fc_air_harbor",
}
BAGGAGE_USERS = {
    "fb_air_iris", "fb_air_jade", "fb_air_kite", "fb_air_lumen",
    "fb_air_mesa", "fb_air_nova", "fb_air_orbit", "fb_air_pine",
}
INSURANCE_RESERVATIONS = {
    "IRSA11", "IRSC33", "IRSD44", "IRSJ00", "IRSF66", "IRSG77", "IRSI99", "IRSL24",
}
NEW_USERS = P4_USERS | CARDINALITY_USERS | BAGGAGE_USERS | {
    "iris_bennett_8711", "keira_davis_8933", "lucas_evans_8044", "rhea_kim_8600",
    "nolan_green_8266", "ophelia_hayes_8377", "quinn_james_8599", "talia_moore_8824",
}
NEW_FLIGHTS = {
    "P4C101", "P4C102", "P4D201", "P4D202", "P4E301", "P4E302", "P4F401", "P4F402",
    "P4G501", "P4G502", "P4H601", "P4H602", "P4J701", "P4J702", "P4K801", "P4K802",
    "FCA101", "FCB202", "FCC303", "FCD404", "FCE505", "FCF606", "FCG707", "FCH808",
    "FBA111", "FBB222", "FBC333", "FBD444", "FBE555", "FBF666", "FBG777", "FBH888",
    "IRS111", "IRS333", "IRS444", "IRJ100", "IRS666", "IRS777", "IRS999", "IRL300",
}


def build_final_airline_db() -> FinalCandidateAirlineDB:
    base = build_core_db().model_dump(mode="json")
    source = build_gate0_db().model_dump(mode="json")
    base["users"].update({key: source["users"][key] for key in NEW_USERS})
    base["flights"].update({key: source["flights"][key] for key in NEW_FLIGHTS})
    base["reservations"].update({
        key: source["reservations"][key] for key in INSURANCE_RESERVATIONS
    })
    base["settlement_contracts"].update({
        key: source["settlement_contracts"][key] for key in INSURANCE_RESERVATIONS
    })
    base["governance_contract"] = source["governance_contract"]
    return add_airline_controls(FinalCandidateAirlineDB.model_validate(base))
