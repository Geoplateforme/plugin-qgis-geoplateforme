class AddTagException(Exception):
    pass


class DeleteUploadException(Exception):
    pass


class ConfigurationCreationException(Exception):
    pass


class CreateProcessingException(Exception):
    pass


class DeleteStoredDataException(Exception):
    pass


class DeleteTagException(Exception):
    pass


class FileUploadException(Exception):
    pass


class InvalidToken(Exception):
    pass


class LaunchExecutionException(Exception):
    pass


class OfferingCreationException(Exception):
    pass


class ReadStoredDataException(Exception):
    pass


class ReadUploadException(Exception):
    pass


class UnavailableConfigurationException(Exception):
    pass


class UnavailableConfigurationsException(Exception):
    pass


class UnavailableDatastoreException(Exception):
    pass


class UnavailableEndpointException(Exception):
    pass


class UnavailableExecutionException(Exception):
    pass


class UnavailableOfferingsException(Exception):
    pass


class UnavailableProcessingException(Exception):
    pass


class UnavailableStoredData(Exception):
    pass


class UnavailableStoredDataException(Exception):
    pass


class UnavailableUploadException(Exception):
    pass


class UnavailableUploadFileTreeException(Exception):
    pass


class UnavailableUserException(Exception):
    pass


class UploadClosingException(Exception):
    pass


class UploadCreationException(Exception):
    pass


class InvalidOAuthPort(ValueError):
    pass


class UnavailablePortException(ConnectionError):
    pass
