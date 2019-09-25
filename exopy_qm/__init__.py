# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2019-2019 by exopy_qm Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
import enaml


def list_manifests():
    """List all the manifest contributed by the package.
    """

    enaml.imports()

    with enaml.imports():
        from .manifest import QmManifest

    return [QmManifest]
