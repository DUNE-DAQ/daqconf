import conffwk

def oks_format(input_file) -> None:
    print(f"Formatting file {input_file}")
    dal = conffwk.dal.module("generated", "schema/confmodel/dunedaq.schema.xml")
    oks_kernel = conffwk.Configuration(f"oksconflibs:{input_file}")

    testobj = dal.Resource("Reformat-test-obj")
    oks_kernel.update_dal(testobj)
    oks_kernel.destroy_dal(testobj)

    oks_kernel.commit()
