# Nornir Nautobot Inventory Configuration

Nornir Inventory takes several configuration options, but can be executed without any options (if you complete the proper environment variables).  

## Configuration Options

There are two required parameters that may be loaded either through configuration or through the environment. 

| Option            | Parameter         | Value                                                                                           | Default             | Environment Variable |
| ----------------- | ----------------- | ----------------------------------------------------------------------------------------------- | ------------------- | -------------------- |
| Nautobot URL      | nautobot_url      | Required: String - The base url of Nautobot (`http://localhost:8000` or `https://nautobot_url`) | env(NAUTOBOT_URL)   | NAUTOBOT_URL         |
| Nautobot Token    | nautobot_token    | Required: String - The token to authenticate to Nautobot API                                    | env(NAUTOBOT_TOKEN) | NAUTOBOT_TOKEN       |
| SSL Verify        | ssl_verify        | Boolean - True or False to verify SSL                                                           | True                |                      |
| Filter Parameters | filter_parameters | Dictionary - Key/value pairs corresponding to Nautobot API searches                             | {}                  |                      |

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

## Construct

Pynautobot will provide for the basic information that is required for Nornir to be able to leverage the inventory. The pynautobot object will also be made available at `host.data.pynautobot_object` to be able to access information provided from the _dcim devices_ endpoint.

## Filtering

With the Nornir Nautobot Inventory plugin you have the option of using all of the Django REST Framework filters. You can pass the options that you use via the API into the inventory to provide additional filtering parameters using the configuration option **filter_parameters** (see next section for examples). This is **not** part of the F filter that comes with Nornir. This is filtering of devices from even entering the inventory.  

> To use the examples in the directory you need to also install into the container/environment `nornir_utils`. The `print_result` function is not included in the base Nornir and to get this utility to print out the full Hello World task you need to have this utility.

## Filtering Examples

For each of the examples the locations correspond to the first three letters of the devices below:

```python
>>> nautobot.dcim.devices.all()
[den-rtr01, den-rtr02, grb-rtr01, msp-rtr01, msp-rtr02, nyc-rtr01, nyc-rtr02]
```

### Filtering Example: Select from single location

To filter from a single location you can use the filter location to get the devices at a single location based on the **Primary Key** for the location:

> NOTE: Location names do not guarantee uniqueness in Nautobot 2.0.
> 
> See this document for more information:
> 
> https://docs.nautobot.com/projects/core/en/next/development/apps/api/platform-features/uniquely-identify-objects/


```python
location = "db913e3b-cbe0-4463-addc-816ba6a20100"

my_nornir = InitNornir(
    inventory={
        "plugin": "NautobotInventory",
        "options": {
            "nautobot_url": os.getenv("NAUTOBOT_URL"),
            "nautobot_token": os.getenv("NAUTBOT_TOKEN"),
            "filter_parameters": {"location": location},
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
root@2e8168a1c3e7:/local# python examples/filter_location.py 
Hosts found: 2
dict_keys(['msp-rtr01', 'msp-rtr02'])
```


### Filter Example: Multiple Locations

To search within multiple locations, pass a list of location Primary Keys. In the example below, it is the same as the previous example with a list passed in instead of a single string.

```python
location = ["db913e3b-cbe0-4463-addc-816ba6a20100", "6f09aa66-96be-4b4d-955a-9c98e488f0e6"]

my_nornir = InitNornir(
    inventory={
        "plugin": "NautobotInventory",
        "options": {
            "nautobot_url": os.getenv("NAUTOBOT_URL"),
            "nautobot_token": os.getenv("NAUTBOT_TOKEN"),
            "filter_parameters": {"location": location},
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
root@2e8168a1c3e7:/local# python examples/filter_multiple_locations.py 
Hosts found: 3
dict_keys(['grb-rtr01', 'msp-rtr01', 'msp-rtr02'])
```

### Filtering Example: Not at a location

The negative filters also are supported. These are all of the filters possible. Here we will search for devices **not** at _MSP_:

```python
not_location = "db913e3b-cbe0-4463-addc-816ba6a20100"

my_nornir = InitNornir(
    inventory={
        "plugin": "NautobotInventory",
        "options": {
            "nautobot_url": os.getenv("NAUTOBOT_URL"),
            "nautobot_token": os.getenv("NAUTBOT_TOKEN"),
            "filter_parameters": {"location__n": not_location},
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
root@2e8168a1c3e7:/local# python examples/filter_negate_location.py 
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