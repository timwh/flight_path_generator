def classFactory(iface):
    from .plugin import FlightPathGeneratorPlugin
    return FlightPathGeneratorPlugin(iface)
