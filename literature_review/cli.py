import argparse
from .pipeline import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args()
    print(run(top_n=args.top_n))


if __name__ == "__main__":
    main()
