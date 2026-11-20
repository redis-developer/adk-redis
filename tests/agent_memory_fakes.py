# Copyright 2025 Redis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Namespace support shared by the fake Redis Agent Memory clients."""

import hashlib
from types import SimpleNamespace


def namespace_id_for(name):
  """Return the namespace ID the fakes assign to a namespace name."""
  return "ns_" + hashlib.md5(name.encode("utf-8")).hexdigest()


class FakeNamespaces:
  """Mixin giving a fake client shared root namespaces.

  Attributes:
      namespaces: Existing namespace names mapped to their IDs.
      created_namespaces: Requests passed to create_namespace_async.
  """

  def init_namespaces(self, *names):
    self.namespaces = {name: namespace_id_for(name) for name in names}
    self.created_namespaces = []

  async def list_namespaces_async(self, *, scope=None, limit=None, cursor=None):
    items = [
        SimpleNamespace(
            namespace_id=namespace_id,
            name=name,
            parent_id=None,
            state="ACTIVE",
        )
        for name, namespace_id in self.namespaces.items()
    ]
    return SimpleNamespace(items=items, next_cursor=None)

  async def create_namespace_async(self, *, request):
    self.created_namespaces.append(request)
    namespace_id = namespace_id_for(request["name"])
    self.namespaces[request["name"]] = namespace_id
    return SimpleNamespace(namespace=SimpleNamespace(namespace_id=namespace_id))
