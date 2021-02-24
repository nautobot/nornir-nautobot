# Nornir Nautobot Inventory Configuration

Nornir Inventory takes several configuration options, but can be executed without any options (if you complete the proper environment variables).  

## Configuration Options

There are two required parameters that may be loaded either through configuration or through the environment. 

| Parameter         | Required | Default | Environment Variable |
| ----------------- | -------- | ------- | -------------------- |
| nautobot_url      | True     |         | NAUTOBOT_URL         |
| nautobot_token    | True     |         | NAUTOBOT_TOKEN       |
| filter_parameters | False    |         |                      |
| ssl_verify        | False    | True    |                      |

## Using Inventory

### Initialization via Environment Variables, No Options

Without any options configured the plugin will search the environment for the URL and TOKEN to be used. This also will validate any certificates for the inventory.

```python
nornir_obj = InitNornir(
    inventory={
        "plugin": "NautobotInventory",
    },
)
```

### Initialization via Configuration

This example shows providing configuration options to set the URL statically, load the configuration of the TOKEN via the environment. This also has SSL verification disabled if required.

```python
my_nornir = InitNornir(
    inventory={
        "plugin": "NautobotInventory",
        "options": {
            "nautobot_url": "http://nautobot.example.com",
            "nautobot_token": os.getenv("NAUTBOT_TOKEN"),
            "ssl_verify": False,
        },
    },
)
```

## Filtering

With the Nornir Nautobot Inventory plugin you have the option of using all of the Django REST Framework filters. You can pass the options that you use via the API into the inventory to provide additional filtering parameters using the configuration option **filter_parameters** (see next section for examples). This is **not** part of the F filter that comes with Nornir. This is filtering of devices from even entering the inventory.  

> To use the examples in the directory you need to also install into the container/environment `nornir_utils`. The `print_result` function is not included in the base Nornir and to get this utility to print out the full Hello World task you need to have this utility.

## Filtering Examples

For each of the examples the sites correspond to the first three letters of the devices below:

```python
>>> nautobot.dcim.devices.all()
[den-rtr01, den-rtr02, grb-rtr01, msp-rtr01, msp-rtr02, nyc-rtr01, nyc-rtr02]
```

### Filtering Example: Select from single site

To filter from a single site you can use the filter site to get the devices at a single site based on the **slug** for the site:

```python
site = "msp"

my_nornir = InitNornir(
    inventory={
        "plugin": "NautobotInventory",
        "options": {
            "nautobot_url": os.getenv("NAUTOBOT_URL"),
            "nautobot_token": os.getenv("NAUTBOT_TOKEN"),
            "filter_parameters": {"site": site},
            "ssl_verify": False,
        },
    },
)

print(f"Hosts found: {len(my_nornir.inventory.hosts)}")
# Print out the keys for the inventory
print(my_nornir.inventory.hosts.keys())
```

This results in:

```
root@2e8168a1c3e7:/local# python examples/filter_site.py 
Hosts found: 2
dict_keys(['msp-rtr01', 'msp-rtr02'])
```


### Filter Example: Multiple Sites

To search within multiple sites, pass a list of site slugs. In the example below, it is the same as the previous example with a list passed in instead of a single string.

```python
site = ["msp", "grb"]

my_nornir = InitNornir(
    inventory={
        "plugin": "NautobotInventory",
        "options": {
            "nautobot_url": os.getenv("NAUTOBOT_URL"),
            "nautobot_token": os.getenv("NAUTBOT_TOKEN"),
            "filter_parameters": {"site": site},
            "ssl_verify": False,
        },
    },
)

print(f"Hosts found: {len(my_nornir.inventory.hosts)}")
# Print out the keys for the inventory
print(my_nornir.inventory.hosts.keys())
```

Results in:

```
root@2e8168a1c3e7:/local# python examples/filter_multiple_sites.py 
Hosts found: 3
dict_keys(['grb-rtr01', 'msp-rtr01', 'msp-rtr02'])
```

### Filtering Example: Not at a site

The negative filters also are supported. These are all of the filters possible. Here we will search for devices **not** at _MSP_:

```python
not_site = "msp"

my_nornir = InitNornir(
    inventory={
        "plugin": "NautobotInventory",
        "options": {
            "nautobot_url": os.getenv("NAUTOBOT_URL"),
            "nautobot_token": os.getenv("NAUTBOT_TOKEN"),
            "filter_parameters": {"site__n": not_site},
            "ssl_verify": False,
        },
    },
)

print(f"Hosts found: {len(my_nornir.inventory.hosts)}")
# Print out the keys for the inventory
print(my_nornir.inventory.hosts.keys())
```

Results in:

```
root@2e8168a1c3e7:/local# python examples/filter_negate_site.py 
Hosts found: 5
dict_keys(['den-rtr01', 'den-rtr02', 'grb-rtr01', 'nyc-rtr01', 'nyc-rtr02'])
```

## Inventory Parameters

Parameter precedence follows:

1. Definition of variable in the configuration
2. Gathered from the environment when not defined by the configuration

### nautobot_url

Default: Environment Variable Look Up
Environment Variable: NAUTOBOT_URL

The base URL of Nautobot. Include the `http://` or `https://` but nothing after the URL. Include the port if it is available on a non standard HTTP (80) or HTTPS (443) port.

### nautobot_token

Default: Environment Variable Look Up
Environment Variable: NAUTOBOT_TOKEN

The token to use to interact with the REST API of Nautobot.

### ssl_verify

Whether or not to verify the certificate from Nautobot.

### filter_parameters

The filtering parameters provided as a dictionary of key/value pairs. The keys should match parameters of DCIM Devices API endpoint. To test the parameters it is recommended to use the API docs (linked at the bottom of Nautobot) to help identify appropriate filter parameters.

## Getting Started with the Examples

You can test out this without installing into your own system following these steps to test yourself. 

### Requirements

* Docker
* Python Invoke (`pip install invoke`)

### Building the Docker container and executing

1. Execute `invoke build` to build a container
2. Execute `invoke cli` to enter into the bash shell

[Home](../index.md)