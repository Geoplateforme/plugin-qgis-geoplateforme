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


class DeleteMetadataException(Exception):
    pass


class DeleteTagException(Exception):
    pass


class FileUploadException(Exception):
    pass


class StaticFileUploadException(Exception):
    pass


class InvalidOAuthConfiguration(ValueError):
    pass


class InvalidOAuthPort(ValueError):
    pass


class InvalidToken(Exception):
    pass


class LaunchExecutionException(Exception):
    pass


class MetadataCreationException(Exception):
    pass


class OfferingCreationException(Exception):
    pass


class ReadStoredDataException(Exception):
    pass


class ReadUploadException(Exception):
    pass


class ReadConfigurationException(Exception):
    pass


class ReadMetadataException(Exception):
    pass


class ReadOfferingException(Exception):
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


class UnavailableMetadataFileException(Exception):
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


class UnavailableMetadataException(Exception):
    pass


class UnavailableUploadFileTreeException(Exception):
    pass


class UnavailableUserException(Exception):
    pass


class UnavailableStaticException(Exception):
    pass


class UploadClosingException(Exception):
    pass


class UploadCreationException(Exception):
    pass


class UnavailablePortException(ConnectionError):
    pass


class ReadUserKeyException(Exception):
    pass


class DeleteUserKeyException(Exception):
    pass


class ReadPermissionException(Exception):
    pass


class DeletePermissionException(Exception):
    pass


class CreatePermissionException(Exception):
    pass
