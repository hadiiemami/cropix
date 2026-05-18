def classFactory(iface):
    from .plugin import Cropix
    return Cropix(iface)