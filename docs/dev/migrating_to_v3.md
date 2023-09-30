# Migrating to v3

This is intended to document the changes and considerations for migration to Nornir-Nautobot 3.0. **Please Note** this is nornir-nautobot's version number, not Nautobot's version number. This major upgrade did coincide with the release of Nautobot 2.0, but the version trains are on their own path.

## Inventory Update

The inventory has been updated to reflect the changes in Nautobot, specifically that `Region` and `Site` have been collapsed into Location. Please see the [inventory docs](../inventory/inventory.md) for the latest documentation.

## Dispatcher Update

The dispatcher function signature has substantially changed. Overall, this will allow for easier configurations to end users and specifically users of Nautobot's Golden Config plugin. Please see the relevant [dispatcher docs](../task/task.md#dispatcher-sender) for the latest documentation.

The dispatcher now prefers senders in the following order, in which `framework` examples would be `netmiko` or `napalm` and `network_driver` examples would be `cisco_ios` or `arista_eos`.

- If there is a custom_dispatcher, **only** use that
- Check for the `framework` and `network_driver`
- Check for the `framework`'s default