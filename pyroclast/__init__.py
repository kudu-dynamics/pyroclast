from pyroclast.schedule import Schedule
from pyroclast.settings import Settings


__all__ = ["Pyroclast"]
__author__ = "elee@kududyn.com"
__version__ = "0.1.0"


class Pyroclast(Schedule, Settings):
    """**The Pyroclast API.**

    Pyroclast provides an opinionated interface to a few useful technologies.

    The goal is to distill expert knowledge--lessons learned, common usage
    patterns, strengths and weaknesses, etc--and prescribe simple APIs for
    the most common use cases.

    - *Nomad*  (as a container/work orchestration tool and resource scheduler)
    """

    pass
