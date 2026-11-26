"""Full offline v28 component acceptance; blocks network and subprocesses."""
from verify_v28_actor_runtime import main


if __name__ == '__main__':
    main(include_method=True)
