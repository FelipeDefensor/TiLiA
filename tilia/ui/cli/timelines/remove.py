from argparse import _SubParsersAction

from tilia.requests import get, Get, Post, post


def setup_parser(subparser: _SubParsersAction):
    remove_subp = subparser.add_parser("remove", exit_on_error=False, aliases=["rm"])
    remove_subcommands = remove_subp.add_subparsers(dest="type", required=True)

    # 'remove by name' subcommand
    remove_by_name_subc = remove_subcommands.add_parser("name", exit_on_error=False)
    remove_by_name_subc.add_argument("name")
    remove_by_name_subc.set_defaults(func=remove_by_name)

    # 'remove by ordinal' subcommand
    remove_by_ordinal_subc = remove_subcommands.add_parser(
        "ordinal", exit_on_error=False
    )
    remove_by_ordinal_subc.add_argument("ordinal", type=int)
    remove_by_ordinal_subc.set_defaults(func=remove_by_ordinal)


def remove_by_name(namespace):
    tl = get(Get.TIMELINE_BY_ATTR, "name", namespace.name)

    if not tl:
        raise ValueError(f"No timeline found with name={namespace.name}")

    print(f"Removing timeline {tl=}")

    post(Post.REQUEST_TIMELINE_DELETE, tl.id)


def remove_by_ordinal(namespace):
    tl = get(Get.TIMELINE_BY_ATTR, "ordinal", namespace.ordinal)

    if not tl:
        raise ValueError(f"No timeline found with ordinal={namespace.ordinal}")

    print(f"Removing timeline {tl=}")

    post(Post.REQUEST_TIMELINE_DELETE, tl.id)
