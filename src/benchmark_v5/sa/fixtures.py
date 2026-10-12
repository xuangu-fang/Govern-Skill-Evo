"""Small hand-written white-box engineering fixtures; not a Benchmark task set."""


def order(key, fixture="flat", profile="low", quantity=4, due=100, release=0):
    return dict(id=key, fixture=fixture, profile=profile, quantity=quantity, due=due, release=release)


def case(key, orders, initial=("flat", "low"), split="engineering_dev", shift_end=200):
    return dict(id=key, world_version="sa-synthetic-v1", split=split, orders=orders,
                initial=list(initial), capacity=4, shift_end=shift_end)


def development():
    return [
        case("SA-D01", [order("o1", profile="high", due=26), order("o2", due=28)]),
        case("SA-D02", [order("o1", profile="high", due=18), order("o2", due=36)]),
        case("SA-D03", [order("o1", quantity=2, due=14), order("o2", quantity=2, due=16)]),
        case("SA-D04", [order("o1", quantity=2, due=14), order("o2", quantity=2, due=30, release=12)]),
        case("SA-D05", [order("o1", "hanging", "high", 3, 22), order("o2", quantity=1, due=38)]),
        case("SA-D06", [order("o1", quantity=5, due=25), order("o2", "hanging", "high", 1, 42)]),
        case("SA-D07", [order("o1", quantity=2, due=80), order("o2", "hanging", "high", 1, 90),
                        order("o3", quantity=3, due=100)], initial=("hanging", "high")),
    ]


def training_fixture():
    return case("SA-E01", [order("j1", quantity=1, due=200), order("j2", quantity=2, due=200),
        order("j3", "hanging", "low", 2, 200), order("j4", "hanging", "high", 1, 200),
        order("j5", "hanging", "low", 1, 200), order("j6", "flat", "high", 2, 200),
        order("j7", "flat", "high", 5, 200)], split="engineering_train")


def training_plan():
    return [{"j1": 1}, {"j2": 2}, {"j3": 2}, {"j4": 1}, {"j5": 1},
            {"j6": 2}, {"j7": 4}, {"j7": 1}]
