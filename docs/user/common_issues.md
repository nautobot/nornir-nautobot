# Common Issues

## No Results with a Filter

If you are getting no results from your inventory and have a filter being applied to the plugin (not filtering hosts after the gathering of the inventory). Then you should take a look at the filter parameters. Making sure that these are in fact filters that can be applied to the DCIM inventory.

## Help - Building Filters

To take a look at the filter keys available, use the Nautobot API browser to find the available options. This includes negating devices if needed based on the Django filters made available.  