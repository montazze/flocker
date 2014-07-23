# Copyright Hybrid Logic Ltd.  See LICENSE file for details.

"""
Tests for ``flocker.node._config``.
"""

from __future__ import unicode_literals, absolute_import

from yaml import safe_load

from twisted.python.filepath import FilePath
from twisted.trial.unittest import SynchronousTestCase
from .._config import ConfigurationError, Configuration, configuration_to_yaml
from .._model import (
    Application, AttachedVolume, DockerImage, Deployment, Node, Port
)


class ApplicationsFromConfigurationTests(SynchronousTestCase):
    """
    Tests for ``Configuration._applications_from_configuration``.
    """
    def test_error_on_missing_application_key(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` if the application_configuration does not
        contain an ``u"application"`` key.
        """
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      {})
        self.assertEqual(
            "Application configuration has an error. "
            "Missing 'applications' key.",
            exception.message
        )

    def test_error_on_missing_version_key(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` if the application_configuration does not
        contain an ``u"version"`` key.
        """
        config = dict(applications={})
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application configuration has an error. "
            "Missing 'version' key.",
            exception.message
        )

    def test_error_on_incorrect_version(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` if the version specified is not 1.
        """
        config = dict(applications={}, version=2)
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application configuration has an error. "
            "Incorrect version specified.",
            exception.message
        )

    def test_error_on_missing_application_attributes(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` if the application_configuration does not
        contain all the attributes of an ``Application`` record.
        """
        config = dict(applications={'mysql-hybridcluster': {}}, version=1)
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Missing value for 'image'.",
            exception.message
        )

    def test_error_on_extra_application_attributes(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` if the application_configuration contains
        unrecognised Application attribute names.
        """
        config = dict(
            version=1,
            applications={
                'mysql-hybridcluster': dict(image='foo/bar:baz', foo='bar',
                                            baz='quux')})
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Unrecognised keys: foo, baz.",
            exception.message
        )

    def test_error_invalid_dockerimage_name(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` if the application_configuration uses invalid
        Docker image names.
        """
        invalid_docker_image_name = ':baz'
        config = dict(
            version=1,
            applications={'mysql-hybridcluster': dict(
                image=invalid_docker_image_name)})
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Invalid Docker image name. "
            "Docker image names must have format 'repository[:tag]'. "
            "Found ':baz'.",
            exception.message
        )

    def test_dict_of_applications(self):
        """
        ``Configuration._applications_from_configuration`` returns a ``dict``
        of ``Application`` instances, one for each application key in the
        supplied configuration.
        """
        config = dict(
            version=1,
            applications={
                'mysql-hybridcluster': dict(
                    image='flocker/mysql:v1.0.0',
                    volume={'mountpoint': b'/var/mysql/data'}
                ),
                'site-hybridcluster': {
                    'image': 'flocker/wordpress:v1.0.0',
                    'ports': [dict(internal=80, external=8080)],
                }
            }
        )
        parser = Configuration()
        applications = parser._applications_from_configuration(config)
        expected_applications = {
            'mysql-hybridcluster': Application(
                name='mysql-hybridcluster',
                image=DockerImage(repository='flocker/mysql', tag='v1.0.0'),
                ports=frozenset(),
                volume=AttachedVolume(
                    name='mysql-hybridcluster',
                    mountpoint=FilePath(b'/var/mysql/data'))),
            'site-hybridcluster': Application(
                name='site-hybridcluster',
                image=DockerImage(repository='flocker/wordpress',
                                  tag='v1.0.0'),
                ports=frozenset([Port(internal_port=80,
                                      external_port=8080)]))
        }
        self.assertEqual(expected_applications, applications)

    def test_ports_missing_internal(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` if the application_configuration has a port
        entry that is missing the internal port.
        """
        config = dict(
            version=1,
            applications={'mysql-hybridcluster': dict(
                image='busybox',
                ports=[{'external': 90}],
                )})
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Invalid ports specification. Missing internal port.",
            exception.message
        )

    def test_ports_missing_external(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` if the application_configuration has a port
        entry that is missing the internal port.
        """
        config = dict(
            version=1,
            applications={'mysql-hybridcluster': dict(
                image='busybox',
                ports=[{'internal': 90}],
                )})
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Invalid ports specification. Missing external port.",
            exception.message
        )

    def test_ports_extra_keys(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` if the application_configuration has a port
        entry that has extra keys.
        """
        config = dict(
            version=1,
            applications={'mysql-hybridcluster': dict(
                image='busybox',
                ports=[{'internal': 90, 'external': 40,
                        'foo': 5, 'bar': 'six'}],
                )})
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Invalid ports specification. Unrecognised keys: bar, foo.",
            exception.message
        )

    def test_error_on_volume_extra_keys(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` error if the volume dictionary contains
        extra keys.
        """
        config = dict(
            version=1,
            applications={'mysql-hybridcluster': dict(
                image='busybox',
                volume={'mountpoint': b'/var/mysql/data',
                        'bar': 'baz',
                        'foo': 215},
            )}
        )
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Invalid volume specification. Unrecognised keys: bar, foo.",
            exception.message
        )

    def test_error_on_volume_missing_mountpoint(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` error if the volume key does not
        contain a mountpoint.
        """
        config = dict(
            version=1,
            applications={'mysql-hybridcluster': dict(
                image='busybox',
                volume={},
            )}
        )
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Invalid volume specification. Missing mountpoint.",
            exception.message
        )

    def test_error_on_volume_invalid_mountpoint(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` error if the specified volume mountpoint is
        not a valid absolute path.
        """
        config = dict(
            version=1,
            applications={'mysql-hybridcluster': dict(
                image='busybox',
                volume={'mountpoint': b'./.././var//'},
            )}
        )
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Invalid volume specification. Mountpoint ./.././var// is not an "
            "absolute path.",
            exception.message
        )

    def test_error_on_volume_mountpoint_not_ascii(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` error if the specified volume mountpoint is
        not a byte string.
        """
        mountpoint_unicode = u'\u2603'
        config = dict(
            version=1,
            applications={'mysql-hybridcluster': dict(
                image='busybox',
                volume={'mountpoint': mountpoint_unicode},
            )}
        )
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Invalid volume specification. Mountpoint {mount} contains "
            "non-ASCII (unsupported).".format(mount=mountpoint_unicode),
            exception.message
        )

    def test_error_on_invalid_volume_yaml(self):
        """
        ``Configuration._applications_from_configuration`` raises a
        ``ConfigurationError`` if the volume key is not a dictionary.
        """
        config = dict(
            version=1,
            applications={'mysql-hybridcluster': dict(
                image='busybox',
                volume='a random string',
            )}
        )
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._applications_from_configuration,
                                      config)
        self.assertEqual(
            "Application 'mysql-hybridcluster' has a config error. "
            "Invalid volume specification. Unexpected value: a random string",
            exception.message
        )


class DeploymentFromConfigurationTests(SynchronousTestCase):
    """
    Tests for ``Configuration._deployment_from_configuration``.
    """
    def test_error_on_missing_nodes_key(self):
        """
        ``Configuration._deployment_from_config`` raises a
        ``ConfigurationError`` if the deployment_configuration does not
        contain an ``u"nodes"`` key.
        """
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._deployment_from_configuration,
                                      {}, set())
        self.assertEqual(
            "Deployment configuration has an error. Missing 'nodes' key.",
            exception.message
        )

    def test_error_on_missing_version_key(self):
        """
        ``Configuration._deployment_from_config`` raises a
        ``ConfigurationError`` if the deployment_configuration does not
        contain an ``u"version"`` key.
        """
        config = dict(nodes={})
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._deployment_from_configuration,
                                      config, set())
        self.assertEqual(
            "Deployment configuration has an error. Missing 'version' key.",
            exception.message
        )

    def test_error_on_incorrect_version(self):
        """
        ``Configuration._deployment_from_config`` raises a
        ``ConfigurationError`` if the version specified is not 1.
        """
        config = dict(nodes={}, version=2)
        parser = Configuration()
        exception = self.assertRaises(ConfigurationError,
                                      parser._deployment_from_configuration,
                                      config, set())
        self.assertEqual(
            "Deployment configuration has an error. "
            "Incorrect version specified.",
            exception.message
        )

    def test_error_on_non_list_applications(self):
        """
        ``_deployment_from_config`` raises a ``ValueError`` if the
        deployment_configuration contains application values not in the form of
        a list.
        """
        config = Configuration()
        exception = self.assertRaises(
            ConfigurationError,
            config._deployment_from_configuration,
            dict(version=1, nodes={'node1.example.com': None}),
            set()
        )
        self.assertEqual(
            'Node node1.example.com has a config error. '
            'Wrong value type: NoneType. '
            'Should be list.',
            exception.message
        )

    def test_error_on_unrecognized_application_name(self):
        """
        ``_deployment_from_config`` raises a ``ValueError`` if the
        deployment_configuration refers to a non-existent application.
        """
        applications = {
            'mysql-hybridcluster': Application(
                name='mysql-hybridcluster',
                image=Application(
                    name='mysql-hybridcluster',
                    image=DockerImage(repository='flocker/mysql',
                                      tag='v1.0.0'))
            )
        }
        config = Configuration()
        exception = self.assertRaises(
            ConfigurationError,
            config._deployment_from_configuration,
            dict(
                version=1,
                nodes={'node1.example.com': ['site-hybridcluster']}),
            applications
        )
        self.assertEqual(
            'Node node1.example.com has a config error. '
            'Unrecognised application name: site-hybridcluster.',
            exception.message
        )

    def test_set_on_success(self):
        """
        ``_deployment_from_config`` returns a set of ``Node`` objects. One for
        each key in the supplied nodes dictionary.
        """
        applications = {
            'mysql-hybridcluster': Application(
                name='mysql-hybridcluster',
                image=Application(
                    name='mysql-hybridcluster',
                    image=DockerImage(repository='flocker/mysql',
                                      tag='v1.0.0'))
            )
        }
        config = Configuration()
        result = config._deployment_from_configuration(
            dict(
                version=1,
                nodes={'node1.example.com': ['mysql-hybridcluster']}),
            applications
        )

        expected = set([
            Node(
                hostname='node1.example.com',
                applications=frozenset(applications.values())
            )
        ])

        self.assertEqual(expected, result)


class ModelFromConfigurationTests(SynchronousTestCase):
    """
    Tests for ``Configuration.model_from_configuration``.
    """
    def test_model_from_configuration_empty(self):
        """
        ``Configuration.model_from_configuration`` returns an empty
        ``Deployment`` object if supplied with empty configurations.
        """
        config = Configuration()
        application_configuration = {'applications': {}, 'version': 1}
        deployment_configuration = {'nodes': {}, 'version': 1}
        result = config.model_from_configuration(
            application_configuration, deployment_configuration)
        expected_result = Deployment(nodes=frozenset())
        self.assertEqual(expected_result, result)

    def test_model_from_configuration(self):
        """
        ``Configuration.model_from_configuration`` returns a
        ``Deployment`` object with ``Nodes`` for each supplied node key.
        """
        config = Configuration()
        application_configuration = {
            'version': 1,
            'applications': {
                'mysql-hybridcluster': {'image': 'flocker/mysql:v1.2.3'},
                'site-hybridcluster': {'image': 'flocker/nginx:v1.2.3'}
            }
        }
        deployment_configuration = {
            'version': 1,
            'nodes': {
                'node1.example.com': ['mysql-hybridcluster'],
                'node2.example.com': ['site-hybridcluster'],
            }
        }
        result = config.model_from_configuration(
            application_configuration, deployment_configuration)
        expected_result = Deployment(
            nodes=frozenset([
                Node(
                    hostname='node1.example.com',
                    applications=frozenset([
                        Application(
                            name='mysql-hybridcluster',
                            image=DockerImage(
                                repository='flocker/mysql',
                                tag='v1.2.3'
                            ),
                            ports=frozenset(),
                        ),
                    ])
                ),
                Node(
                    hostname='node2.example.com',
                    applications=frozenset([
                        Application(
                            name='site-hybridcluster',
                            image=DockerImage(
                                repository='flocker/nginx',
                                tag='v1.2.3'
                            ),
                            ports=frozenset(),
                        ),
                    ])
                )
            ])
        )
        self.assertEqual(expected_result, result)


class ConfigurationToYamlTests(SynchronousTestCase):
    """
    Tests for ``Configuration.configuration_to_yaml``.
    """
    def test_no_applications(self):
        """
        A dict with a version and empty applications list are returned if no
        applications are supplied.
        """
        applications = set()
        result = configuration_to_yaml(applications)
        expected = {'applications': {}, 'version': 1}
        self.assertEqual(safe_load(result), expected)

    def test_one_application(self):
        """
        A dictionary of application name -> image is produced where there
        is only one application in the set passed to the
        ``configuration_to_yaml`` method.
        """
        applications = {
            Application(
                name='mysql-hybridcluster',
                image=Application(
                    name='mysql-hybridcluster',
                    image=DockerImage(repository='flocker/mysql',
                                      tag='v1.0.0'))
            )
        }
        result = configuration_to_yaml(applications)
        expected = {
            'applications':
                {'mysql-hybridcluster': {'image': 'unknown', 'ports': []}},
                'version': 1
        }
        self.assertEqual(safe_load(result), expected)

    def test_multiple_applications(self):
        """
        The dictionary includes a representation of each supplied application.
        """
        applications = {
            Application(
                name='mysql-hybridcluster',
                image=Application(
                    name='mysql-hybridcluster',
                    image=DockerImage(repository='flocker/mysql',
                                      tag='v1.0.0'))
            ),
            Application(
                name='site-hybridcluster',
                image=DockerImage(repository='flocker/wordpress',
                                  tag='v1.0.0')
            )
        }
        result = configuration_to_yaml(applications)
        expected = {
            'applications': {
                'site-hybridcluster': {
                    'image': 'unknown',
                    'ports': []
                },
                'mysql-hybridcluster': {'image': 'unknown', 'ports': []}
            },
            'version': 1
        }
        self.assertEqual(safe_load(result), expected)

    def test_application_ports(self):
        """
        The dictionary includes a representation of each supplied application,
        including exposed internal and external ports where the
        ``Application`` specifies these.
        """
        applications = {
            Application(
                name='site-hybridcluster',
                image=DockerImage(repository='flocker/wordpress',
                                  tag='v1.0.0'),
                ports=frozenset([Port(internal_port=80,
                                      external_port=8080)])
            )
        }
        result = configuration_to_yaml(applications)
        expected = {
            'applications': {
                'site-hybridcluster': {
                    'image': 'unknown',
                    'ports': [{'internal': 80, 'external': 8080}]
                },
            },
            'version': 1
        }
        self.assertEqual(safe_load(result), expected)

    def test_application_with_volume_includes_mountpoint(self):
        """
        If the supplied applications have a volume, the resulting yaml will
        also include the volume mountpoint.
        """
        applications = {
            Application(
                name='mysql-hybridcluster',
                image=DockerImage(repository='flocker/mysql', tag='v1.0.0'),
                ports=frozenset(),
                volume=AttachedVolume(
                    name='mysql-hybridcluster',
                    mountpoint=FilePath(b'/var/mysql/data'))
            ),
            Application(
                name='site-hybridcluster',
                image=DockerImage(repository='flocker/wordpress',
                                  tag='v1.0.0'),
                ports=frozenset([Port(internal_port=80,
                                      external_port=8080)])
            )
        }
        result = configuration_to_yaml(applications)
        expected = {
            'applications': {
                'site-hybridcluster': {
                    'image': 'unknown',
                    'ports': [{'internal': 80, 'external': 8080}]
                },
                'mysql-hybridcluster': {
                    'volume': {'mountpoint': '/unknown'},
                    'image': 'unknown',
                    'ports': []
                }
            },
            'version': 1
        }
        self.assertEqual(safe_load(result), expected)

    def test_yaml_parsable_configuration(self):
        """
        The YAML output of ``configuration_to_yaml`` can be successfully
        parsed and then loaded in to ``Application``\ s by
        ``Configuration._applications_from_configuration``
        """
        applications = {
            Application(
                name='mysql-hybridcluster',
                image=DockerImage(repository='flocker/mysql', tag='v1.0.0'),
                ports=frozenset(),
                volume=AttachedVolume(
                    name='mysql-hybridcluster',
                    mountpoint=FilePath(b'/var/mysql/data'))
            ),
            Application(
                name='site-hybridcluster',
                image=DockerImage(repository='flocker/wordpress',
                                  tag='v1.0.0'),
                ports=frozenset([Port(internal_port=80,
                                      external_port=8080)])
            )
        }
        expected_applications = {
            b'mysql-hybridcluster': Application(
                name=b'mysql-hybridcluster',
                image=DockerImage(repository='unknown'),
                ports=frozenset(),
                volume=AttachedVolume(
                    name=b'mysql-hybridcluster',
                    mountpoint=FilePath(b'/unknown')
                )
            ),
            b'site-hybridcluster': Application(
                name=b'site-hybridcluster',
                image=DockerImage(repository='unknown'),
                ports=frozenset([Port(internal_port=80,
                                      external_port=8080)])
            )
        }
        result = configuration_to_yaml(applications)
        config = Configuration()
        apps = config._applications_from_configuration(safe_load(result))
        self.assertEqual(apps, expected_applications)
