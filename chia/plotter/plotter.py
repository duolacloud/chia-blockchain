import click

from chia import __version__
from chia.util.default_root import DEFAULT_ROOT_PATH
from pathlib import Path

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

DEFAULT_STRIPE_SIZE = 65536


def monkey_patch_click() -> None:
    # this hacks around what seems to be an incompatibility between the python from `pyinstaller`
    # and `click`
    #
    # Not 100% sure on the details, but it seems that `click` performs a check on start-up
    # that `codecs.lookup(locale.getpreferredencoding()).name != 'ascii'`, and refuses to start
    # if it's not. The python that comes with `pyinstaller` fails this check.
    #
    # This will probably cause problems with the command-line tools that use parameters that
    # are not strict ascii. The real fix is likely with the `pyinstaller` python.

    import click.core

    click.core._verify_python3_env = lambda *args, **kwargs: 0  # type: ignore


@click.group(
    help=f"\n  Manage chia blockchain infrastructure ({__version__})\n",
    epilog="Try 'chia start node', 'chia netspace -d 192', or 'chia show -s'",
    context_settings=CONTEXT_SETTINGS,
)
@click.option("--root-path", default=DEFAULT_ROOT_PATH, help="Config file root", type=click.Path(), show_default=True)
@click.pass_context
def cli(ctx: click.Context, root_path: str) -> None:
    from pathlib import Path

    ctx.ensure_object(dict)
    ctx.obj["root_path"] = Path(root_path)

    """Create, add, remove and check your plots"""
    from chia.util.chia_logging import initialize_logging

    root_path: Path = ctx.obj["root_path"]
    if not root_path.is_dir():
        raise RuntimeError("Please initialize (or migrate) your config directory with 'chia init'")
    initialize_logging("", {"log_stdout": True}, root_path)

@cli.command("version", short_help="Show chia version")
def version_cmd() -> None:
    print(__version__)


@cli.command("run_daemon", short_help="Runs chia daemon")
@click.pass_context
def run_daemon_cmd(ctx: click.Context) -> None:
    from chia.daemon.server import async_run_daemon
    import asyncio

    asyncio.get_event_loop().run_until_complete(async_run_daemon(ctx.obj["root_path"]))

@click.command("create", short_help="Create plots")
@click.option("-k", "--size", help="Plot size", type=int, default=32, show_default=True)
@click.option("--override-k", help="Force size smaller than 32", default=False, show_default=True, is_flag=True)
@click.option("-b", "--buffer", help="Megabytes for sort/plot buffer", type=int, default=3389, show_default=True)
@click.option("-r", "--num_threads", help="Number of threads to use", type=int, default=2, show_default=True)
@click.option("-u", "--buckets", help="Number of buckets", type=int, default=128, show_default=True)
@click.option(
    "-a",
    "--alt_fingerprint",
    type=int,
    default=None,
    help="Enter the alternative fingerprint of the key you want to use",
)
@click.option(
    "-c",
    "--pool_contract_address",
    type=str,
    default=None,
    help="Address of where the pool reward will be sent to. Only used if alt_fingerprint and pool public key are None",
)
@click.option("-f", "--farmer_public_key", help="Hex farmer public key", type=str, default=None)
@click.option("-p", "--pool_public_key", help="Hex public key of pool", type=str, default=None)
@click.option(
    "-t",
    "--tmp_dir",
    help="Temporary directory for plotting files",
    type=click.Path(),
    default=Path("."),
    show_default=True,
)
@click.option("-2", "--tmp2_dir", help="Second temporary directory for plotting files", type=click.Path(), default=None)
@click.option(
    "-d",
    "--final_dir",
    help="Final directory for plots (relative or absolute)",
    type=click.Path(),
    default=Path("."),
    show_default=True,
)
@click.option("-i", "--plotid", help="PlotID in hex for reproducing plots (debugging only)", type=str, default=None)
@click.option("-m", "--memo", help="Memo in hex for reproducing plots (debugging only)", type=str, default=None)
@click.option("-e", "--nobitfield", help="Disable bitfield", default=False, is_flag=True)
@click.option(
    "-x", "--exclude_final_dir", help="Skips adding [final dir] to harvester for farming", default=False, is_flag=True
)
@click.option("-h", "--phase", help="phase", type=int, default=0)
@click.pass_context
def create_cmd(
    ctx: click.Context,
    size: int,
    override_k: bool,
    buffer: int,
    num_threads: int,
    buckets: int,
    alt_fingerprint: int,
    pool_contract_address: str,
    farmer_public_key: str,
    pool_public_key: str,
    tmp_dir: str,
    tmp2_dir: str,
    final_dir: str,
    plotid: str,
    memo: str,
    nobitfield: bool,
    exclude_final_dir: bool,
    phase: int,
):
    from chia.plotting.create_plot import create_plot

    class Params(object):
        def __init__(self):
            self.size = size
            self.buffer = buffer
            self.num_threads = num_threads
            self.buckets = buckets
            self.stripe_size = DEFAULT_STRIPE_SIZE
            self.alt_fingerprint = alt_fingerprint
            self.pool_contract_address = pool_contract_address
            self.farmer_public_key = farmer_public_key
            self.pool_public_key = pool_public_key
            self.tmp_dir = Path(tmp_dir)
            self.tmp2_dir = Path(tmp2_dir) if tmp2_dir else None
            self.final_dir = Path(final_dir)
            self.plotid = plotid
            self.memo = memo
            self.nobitfield = nobitfield
            self.exclude_final_dir = exclude_final_dir
            self.phase = phase

    if size < 32 and not override_k:
        print("k=32 is the minimum size for farming.")
        print("If you are testing and you want to use smaller size please add the --override-k flag.")
        sys.exit(1)
    elif size < 25 and override_k:
        print("Error: The minimum k size allowed from the cli is k=25.")
        sys.exit(1)

    print('create_plot')
    create_plot(Params(), ctx.obj["root_path"])


cli.add_command(create_cmd)


def main() -> None:
    monkey_patch_click()
    cli()  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
