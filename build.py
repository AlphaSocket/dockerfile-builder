#!/usr/bin/env python3
#
# Google Python Style Guide
# 
# module_name, package_name
# GLOBAL_CONSTANT_NAME, 
# global_var_name, local_var_name
# function_name, function_parameter_name
# ClassName, method_name, instance_var_name
# ExceptionName
#
from Globals import *
import os

class Builder():

    conf = OrderedDict()
    envvars = OrderedDict()
    docker_imports = []
    docker_envvars = []
    unparsed_variables = {}
    
    def resolve_env_var(self, envvars):
        result = OrderedDict()
        for key,value in envvars.items():
            variable_name = str(key).upper()

            if type(value) not in [dict,OrderedDict]:
                result[variable_name] = value
            elif is_parsable(value):
                result[variable_name] = value
            else:
                prefix = variable_name + "_"
                resolved_vars = self.resolve_env_var(value)
                for key,value in resolved_vars.items():
                    variable_name = str(key).upper()
                    result[prefix + variable_name] = value
        return result

    def import_stage_env(self, stage, parse=True):
        # CHeck if all var are parsed
        all_parsed = True
        if 'envvars' in self.conf[stage]:
            envvars = self.conf[stage]['envvars']
            envvars = self.resolve_env_var(envvars)
            concat = ""

            for name,value in envvars.items():
                name = "{stage}_{name}".format(stage=str(stage).upper(), name=name)
                if value is None:
                    value = ""
                if parse is True:
                    #print('parsing var: ',name,value, is_parsable(value), parse_content(value) )
                    if is_parsable(value):
                        if 'valueFromCommand' in value:
                            unparsed_value = value['valueFromCommand']
                        elif 'valueFromParse' in value:
                            unparsed_value = value['valueFromParse']
                        else:
                            unparsed_value = ""
                        #print('Unparsed and value: ',unparsed_value,value)
                        parsed_value = parse_content(value)
                        
                        if unparsed_value != parsed_value and 'OrderedDict' not in str(parsed_value):
                            value = parsed_value
                            if name in self.unparsed_variables:
                                del(self.unparsed_variables[name])
                            export_var(name,value)
                        else:
                            self.unparsed_variables[name] = unparsed_value
                            all_parsed = False
                    else:
                        export_var(name,value)
                
                #print('exporting var: ',name,value)
                
                # Keep a list of stage envvars in builder envvars
                if stage not in self.envvars:
                    self.envvars[stage] = OrderedDict()
                self.envvars[stage][name] = value
                concat = concat + '{name}="{value}"\n'.format(name=name,value=value)
                
                if stage in ['general', 'build', 'setup', 'config']:
                    # Workaround quotes
                    if type(value) is str and value.startswith("'") and value.endswith("'"):
                        # Single quotes
                        self.docker_envvars.append("{name}={value}".format(name=name,value=value))
                    else:
                        # Double quotes
                        self.docker_envvars.append('{name}="{value}"'.format(name=name,value=value))
                    # Workaround strings

            export_var('DOCKERFILE_BUILDER_{stage}_ENVVARS'.format(stage=stage.upper()), concat)
        return all_parsed

    def import_stage_files(self, stage):
        if 'imports' in self.conf[stage]:
            files = self.conf[stage]['imports']

            if type(files) is list:
                files = list_to_dict(files)

            # Breaking format source:target
            for key,value in files.items():
                value = os.path.expandvars(value)
                paths = value.split(':')
                
                source_path = paths[0]
                build_path = paths[1]
                
                prefix = os.environ['BUILDER_TARGETS_FOLDERS_BUILD_IMPORTS'] + '/'
                
                if source_path[0:len(prefix)] != prefix:
                    source_path = '{0}/{1}'.format(
                        os.environ['BUILDER_TARGETS_FOLDERS_BUILD_IMPORTS'],
                        source_path
                    )
                
                ## Add file by file to not override previous injected files
                if source_path and build_path:
                    # Source is file
                    if os.path.isfile(source_path):
                        self.docker_imports.append({"source":source_path, "target":build_path})
                    # Source is dir
                    else:
                        tree = self.build_folder_imports(source_path, build_path);
                        for file_source_path, file_build_path in tree:
                            self.docker_imports.append({"source":file_source_path, "target":file_build_path})

    def build_folder_imports(self, source_path, build_path):
        tree=[]
        source_path_lenght = len(source_path)
        for dirpath, dirnames, filenames in os.walk(source_path):
            
            for filename in filenames:
                # Replacing source patch with build path in dirpath
                build_dirpath = build_path + dirpath[source_path_lenght:] 
                
                file_source_path = dirpath + '/' + filename
                file_build_path = build_dirpath + '/' + filename
                tree.append([file_source_path,file_build_path])
        return tree

    def build_all_stage_processes(self, stage, commands_prefix="", row_prefix=""):
        self.build_stage_processes( stage, 'processes_before' )
        self.build_stage_processes( stage, 'processes', commands_prefix, row_prefix )
        self.build_stage_processes( stage, 'processes_after' )
    
    def build_stage_processes(self, stage, kind, commands_prefix="", row_prefix=""):
        imploded_processes=""
        
        if kind in self.conf[stage]:
            # Gather processes
            processes = self.conf[stage][kind]

            # Concat processes
            imploded_processes = self.implode_processes(processes,commands_prefix,row_prefix)

            # Expand env vars in test files ( Outside container env )
            if self.conf['stages'][stage]['expand_vars']['processes'] == True:
                imploded_processes = os.path.expandvars(imploded_processes)
                
        # Export var to env
        export_var(
            '{stage}_{kind}'.format(
                stage=stage.upper(),
                kind=kind.upper()
            ),
            imploded_processes
        )

    def implode_processes(self, processes, commands_prefix="", row_prefix=""):
        concat = ""

        for process in processes:
            concat += "# {title}\n".format(title=process['title'])
            concat += 'echo "### {title}..."\n'.format(title=process['title'])

            commands = else_commands = ""

            for command in process['commands']:
                if 'shell_condition' in process:
                    commands += "    {row_prefix}".format(row_prefix=row_prefix)
                    # Add final ; only if necessary
                    if command.endswith(';'):
                        command_suffix = '\n'
                    else:
                        command_suffix = ';\n'
                else:
                    commands += commands_prefix
                    command_suffix = '\n'

                commands += "{command}{command_suffix}".format(
                                command=command,
                                command_suffix=command_suffix
                            )
                
            if 'else' in process:
                else_commands = "else \n    "
                for else_command in process['else']:
                    else_command_prefix="    "
                    # Add final ; only if necessary
                    if else_command.endswith(';'):
                        else_command_suffix = '\n'
                    else:
                        else_command_suffix = ';\n'
                    else_commands += "{else_command_prefix}{else_command}{else_command_suffix}".format(
                                else_command_prefix=else_command_prefix,
                                else_command=else_command,
                                else_command_suffix=else_command_suffix
                            )

            if 'shell_condition' in process:
                string = "{commands_prefix}if [ {condition} ]; then\n{commands}{else_commands}{row_prefix}fi\n"
                concat += string.format(
                            commands_prefix=commands_prefix,
                            condition=process['shell_condition'],
                            commands=commands,
                            else_commands=else_commands,
                            row_prefix=row_prefix
                        )
            else:
                concat += commands + "\n"
        return concat
            
    def eval_template(self, template, mode=None):
        
        template_file = "{builder_path}/{template_folder}/{template_key}".format(
            builder_path=GLOBALS['locations']['dockerfile-builder'],
            template_folder=self.conf['builder']['folders']['templates'],
            template_key=self.conf['builder']['templates'][template]
        )
        
        target_file = "{pwd}/{template_target}".format(
            pwd=GLOBALS['locations']['pwd'],
            template_target=os.environ['BUILDER_TARGETS_BUILD_{0}'.format(template.upper())]
        )
        
        prepare_file(target_file)
        target_handler = open(target_file, "w");

        with open(template_file, "r") as template_file_handler:
            content = os.path.expandvars(template_file_handler.read())
            if template == "test":
                content = os.path.expandvars(content)
            target_handler.write(content)
        
        target_handler.close()
        template_file_handler.close()

        if mode is not None:
            os.chmod(target_file, mode);

    def rm_template_target(self, template):
        target_file = "{pwd}/{template_target}".format(
            pwd=GLOBALS['locations']['pwd'],
            template_target=os.environ['BUILDER_TARGETS_BUILD_{0}'.format(template.upper())]
        )
        if target_file and os.path.isfile(target_file):
            os.remove(target_file)
        
    def verify_test_file(self):
        if verify_yaml_file(os.environ['BUILDER_TARGETS_BUILD_TRAVIS']) == False:
            print_error('Invalid travis file')
            exit(1)

    def build_builder_env(self):
        # Build args
        docker_args = ""
        build_args = ""
        if 'args' in self.conf['build']:
            for arg,value in self.conf['build']['args'].items():
                docker_args += "ARG BUILD_{0}\n".format(arg.upper())
                build_args += "--build-arg BUILD_{0}={1} ".format(arg.upper(),value)
        export_var('DOCKERFILE_BUILDER_ARGS', docker_args)
        export_var('BUILD_ARGS', build_args)
        
        # Build env file
        docker_env  = "ENV"
        for envvar in self.docker_envvars:
            docker_env += " \\\n\t" + envvar 
        export_var('DOCKERFILE_BUILDER_ENVVARS', docker_env)

        # Expose ports
        docker_ports=""
        if 'ports' in self.conf['build']['envvars'] and bool(os.environ['BUILD_PORTS_MAIN']):
            docker_ports = "EXPOSE {main} {additional}".format(
                main=os.environ['BUILD_PORTS_MAIN'],
                additional=os.environ['BUILD_PORTS_ADDITIONAL']
            )
        export_var('DOCKERFILE_BUILDER_PORTS', docker_ports)

        # WORKDIR
        workdir=""
        if 'workdir' in self.conf['build']['envvars']:
            workdir='WORKDIR {workdir}'.format(workdir=os.environ['BUILD_WORKDIR'])
        export_var( 'DOCKERFILE_BUILDER_WORKDIR', workdir )
        
        # IMPORTS
        concat = ""
        for imported in self.docker_imports:
            concat += "ADD {source} {target}\n".format(
                source=imported['source'],
                target=imported['target']
            )
        # Exporting env variable
        export_var('DOCKERFILE_BUILDER_IMPORTS', concat)
        
        # CACHE docker images
        export_var('DOCKERFILE_BUILDER_CACHE_DOCKER_IMAGES', os.path.expandvars(' '.join(self.conf['cache']['docker_images'])))
        
        # GENERATE USERS AND GROUPS
        template="alpine_config_users_groups"
        alpine_config_users_groups_process = get_command_output(
            "cat {builder_path}/{template_folder}/{template_key}".format(
                builder_path=GLOBALS['locations']['dockerfile-builder'],
                template_folder=self.conf['builder']['folders']['templates'],
                template_key=self.conf['builder']['templates'][template]
            )
        )
        export_var('DOCKERFILE_BUILDER_ALPINE_CONFIGURE_USERS_AND_GROUPS_PROCESS', alpine_config_users_groups_process)
        
        # Hardening
        template="alpine_hardening"
        alpine_hardening_processes = get_command_output(
            "cat {builder_path}/{template_folder}/{template_key}".format(
                builder_path=GLOBALS['locations']['dockerfile-builder'],
                template_folder=self.conf['builder']['folders']['templates'],
                template_key=self.conf['builder']['templates'][template]
            )
        )
        export_var('DOCKERFILE_BUILDER_ALPINE_HARDENING', alpine_hardening_processes)
        
    def build_project_env(self):
        os.environ['PROJECT_TITLE'] = self.conf['project']['title']
        os.environ['PROJECT_CODENAME'] = self.conf['project']['codename']
        os.environ['PROJECT_DESCRIPTION'] = self.conf['project']['description']
        
        # Version 
        if os.environ['BUILD_BRANCH'] == 'master':
            os.environ['PROJECT_VERSION'] = "latest"
        else:
            os.environ['PROJECT_VERSION'] = os.environ['BUILD_VERSION']

        # Format versions
        branches = get_command_output("git for-each-ref --format='%(refname:short)' refs/heads/").split("\n")
        concat = ""
        for line in branches:
            if "master" != line:
                concat += "- {line}\n".format(line=line)
        os.environ['PROJECT_VERSIONS'] = concat

        # Configurable envvars
        os.environ['PROJECT_CONF_ENVVARS'] = os.environ['DOCKERFILE_BUILDER_CONFIG_ENVVARS']

        # Format dependencies
        os.environ['PROJECT_PACKAGES'] = ""
        for stage in ['setup', 'config', 'runtime']:
            label = 'SETUP_DEPENDENCIES_{ucstage}'.format(ucstage=stage.upper())
            if label in os.environ:
                dependencies = str(os.environ[label]).strip().split()
                if dependencies:
                    os.environ['PROJECT_PACKAGES'] += "- {stage} dependencies:\n".format(stage=stage.title())
                    for package in dependencies:
                        if not bool(package):
                            package = 'None'
                        os.environ['PROJECT_PACKAGES'] += "  + {package}\n".format(package=package)
                        
    def build_travis_env(self):
        if 'TEST_NOTIFICATION_WEBHOOK' in os.environ and bool(os.environ['TEST_NOTIFICATION_WEBHOOK']):
            notification_value="notifications:\n    webhooks: " + os.environ['TEST_NOTIFICATION_WEBHOOK']
        else:
            notification_value=""
        export_var('TEST_NOTIFICATION_WEBHOOK', notification_value)

    def import_envvars(self):
        stages = []
        # Set correct order of import
        stages.append('project')
        stages.append('builder')
        stages.append('general')
        stages.append('build')
        stages.append('setup')
        stages.append('config')
        stages.append('test')
        stages.append('push')
        stages.append('cache')

        # Import env var until all unparsed values are parsed
        all_parsed = False
        counter = 0
        while all_parsed is False:
            counter += 1
            # Put a limit to while cycle
            if counter >= 15:
                for name,unparsed_value in self.unparsed_variables.items():
                    print_error("Error: can't parse value \"{}\" for {} ".format(unparsed_value, name) )
                exit(1)
            # Reset docker_envvars
            self.docker_envvars = []
            # Import var parsing data correctly (having already the value for early run)
            all_parsed = True
            for stage in stages:
                result = self.import_stage_env(stage)
                if result is False:
                    all_parsed = False
        
    def import_files(self):
        self.import_stage_files('builder')
        self.import_stage_files('build')
        
    def build_processes(self):
        # Build setup processes
        self.build_all_stage_processes('setup')
        # Build config processes
        self.build_all_stage_processes('config')
        # Build test processes
        self.build_all_stage_processes('test')
         # Build travis processes
        self.build_all_stage_processes('travis', ' - ', "    ")
        
    def __init__(self):

        # Import dockerfile-builder GLOBALS
        dir_path = os.path.dirname(os.path.realpath(__file__))
        import_globals(dir_path + "/globals.yaml")
        from Globals import GLOBALS

        # Import configurations
        config_yaml_path = get_path("{}/{}".format( GLOBALS['locations']['dockerfile-builder'], "config.yaml" ))
        configurations = get_data_from_yaml(config_yaml_path, True)
        dict_merge(self.conf, configurations)
        
        # Import build config
        build_yaml = get_path("{}/{}".format( GLOBALS['locations']['pwd'], self.conf['file']['name'] ))
        build_config = get_data_from_yaml(build_yaml, True)
        # Merge build over defaults
        build_config = dict_merge(self.conf['defaults'], build_config)
        # Import build conf in conf
        self.conf = dict_merge(self.conf, build_config)
        
        # import pprint
        # pp = pprint.PrettyPrinter(indent=0)
        # pp.pprint( self.conf )
        
        # Duplicate test for travis build
        self.conf['travis'] = self.conf['test']
        
        #
        # IMPORT
        #
        # Build env vars for every stage
        print_message('Importing enviroment variables')
        self.import_envvars()
        # Import files
        print_message('Importing files in build')
        self.import_files()
        # Build setup processes
        print_message('Importing processes')
        self.build_processes()

    def build(self):
        #
        # BUILD
        # Building files from templates
        #
        self.build_project_env()
        self.build_builder_env()
        self.build_travis_env()
        
        print_message('Building files')
        cur_branch = os.environ['BUILD_BRANCH']
        if cur_branch not in self.conf['builder']['branch2templates']:
            cur_branch = 'default'
        other_branches = list(self.conf['builder']['branch2templates'].keys())
        other_branches.remove(cur_branch)
        
        # Remove other branch templates
        for other_branch in other_branches:
            for template in self.conf['builder']['branch2templates'][other_branch]:
                self.rm_template_target(template['key'])
            
        if os.environ['BUILD_BRANCH'] != 'master':
            self.verify_test_file()
            
        # Create cur branch templates
        for template in self.conf['builder']['branch2templates'][cur_branch]:
            key = template['key']
            if 'mode' in template:
                mode = int(str(template['mode']), 8)
            else:
                mode = None
            self.eval_template(key, mode)
        
        print_success("Completed")

# ---------

# Init
builder = Builder()
# Build
builder.build()
