import conffwk
import oks

def oks_format(input_file) -> None:
    if ".data.xml" in input_file:
        print(f"Formatting database file {input_file}")
        dal = conffwk.dal.module("generated", "schema/confmodel/dunedaq.schema.xml")
        oks_kernel = conffwk.Configuration(f"oksconflibs:{input_file}")

        testobj = dal.Service("Reformat-test-obj")
        oks_kernel.update_dal(testobj)
        oks_kernel.destroy_dal(testobj)

        oks_kernel.commit()
    elif ".schema.xml" in input_file:
        print(f"Formatting schema file {input_file}")
        
        oks_kernel = oks.OksKernel()
        schema = oks_kernel.load_schema(str(input_file))
        #oks_kernel.save_all_schema()
        oks_kernel.save_as_schema(str(input_file), schema)

    else:
        print(f"Don't know how to handle file {input_file}")
