Code examples
=============

If you want to use my epic pattern matching function it's super easy and would have been even easier if I only knew somebody would want to do that.

 .. doctest::

    >>> from ghia.ghia_cmd import GHIASolver
    >>> from ghia.ghia_web import *
    >>> import re
    >>> solver = GHIASolver(load_config("../credential.cfg"), load_config("../rules.cfg"), ("foo", "bar"))
    >>> pattern_list = []
    >>> pattern_list.append(re.compile("[d-yD]{5}"))
    >>> string = "Derpy is best pony."
    >>> other_string = "MLP G4 is over :("
    >>> solver.does_any_pattern_match(pattern_list, string)
    True
    >>> solver.does_any_pattern_match(pattern_list, other_string)
    False

Sadly this outputs on stderr and the doctest does not see it, so the output cannot be verified.
I wrote this, so i'm leaving it here.

 .. doctest::

    >>> import click
    >>> from ghia.github_communicator import GithubCommunicator
    >>> gcom = GithubCommunicator("abc", "foo", "bar")
    >>> gcom.write_error("You cannot stop the pony references. I am bored out of my mind.", 4)
    >>> click.secho("      Λ", bold=True, fg="red", err=True)
    >>> click.secho(" That | is not an error, it is a test of an error writing function.", bold=True, fg="red", err=True)

And this is how you namedrop Twinkle Sprinkle

 .. doctest::

    >>> from ghia.ghia_cmd import GHIASolver
    >>> from ghia.ghia_web import *
    >>> import re
    >>> solver = GHIASolver(load_config("../credential.cfg"), load_config("../rules.cfg"), ("foo", "bar"))
    >>> solver.namedrop_assignee(GHIASolver.ADD, "Twinkle_Sprinkle")
       + Twinkle_Sprinkle
    >>> solver.namedrop_assignee(GHIASolver.REMOVE, "Twinkle_Sprinkle")
       - Twinkle_Sprinkle
    >>> solver.namedrop_assignee(GHIASolver.LEAVE, "Twinkle_Sprinkle")
       = Twinkle_Sprinkle
