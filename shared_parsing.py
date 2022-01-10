from array import array
import struct, json, os
import time

data_cs = open('data.cs', 'r').read()

data_cs = data_cs.replace('    ', '').replace('\t', '').replace('\n\n', '\n')
data_cs = data_cs.split('\n[StructLayout(LayoutKind.Sequential, Pack = 1)]\n')
for i in range(len(data_cs)):
    data_cs[i] = data_cs[i].split('\n')
    data_cs[i] = [data_cs[i] if (data_cs[i].startswith('public') or data_cs[i].startswith('internal') or data_cs[i].startswith('[MarshalAs')) else 'public ' + data_cs[i] for data_cs[i] in data_cs[i] if data_cs[i] != '' and not data_cs[i].startswith('//')]

    # new_data = []
    # size_const = -1
    # for line in data_cs[i]:
    #     if line.startswith('[MarshalAs'):
    #         size_const = int(line[line.index('SizeConst = ') + len('SizeConst = '):line.index(')')])
    #         new_data.append(line)
    #         continue

    #     if '[' in line:
    #         for j in range(size_const):
    #             new_data.append(line.replace('[', '').replace(']', ''))
    #         continue
        
    #     new_data.append(line)
    # data_cs[i] = new_data


formatted_data = {}
for struct_ in data_cs:
    if struct_ == []:
        continue
    name = struct_[0].split()[2]
    has_type = False
    if '<' in name:
        name = name.split('<')[0]
        has_type = True
    
    formatted_data[name] = (has_type, struct_[2:-1])

# print(formatted_data['Shared'])

sizes = {"Int32": 4, "Int16": 2, "Int8": 1, "Float32": 4, "Float64": 8, "Double": 8, "Single": 4, "UInt32": 4, "UInt16": 2, "UInt8": 1, "Int64": 8, "UInt64": 8, "Boolean": 1, "Byte": 1, "SByte": 1, "Char": 2, "String": 4, "Void": 0, "byte": 1, "sbyte": 1, "char": 2, "string": 4, "void": 0}

found_names = []
found_funcs = []

def get_array_size(marshal_line, next_line):
    line_type = next_line.split(' ')[1][:-2]
    if line_type in sizes:
        return int(marshal_line[marshal_line.index('SizeConst = ') + len('SizeConst = '):marshal_line.index(')')]) * sizes[line_type]
    return int(marshal_line[marshal_line.index('SizeConst = ') + len('SizeConst = '):marshal_line.index(')')]) * get_struct_size(line_type)()

def get_struct_size(struct_name):
    if struct_name in found_names:
        return found_funcs[found_names.index(struct_name)]
    if struct_name in sizes:
        return lambda: sizes[struct_name]
    
    has_type, struct = formatted_data[struct_name]
    total_numaric = 0
    total_ts = 0
    for i, line in enumerate(struct):
        if line.startswith('[MarshalAs'):
            total_numaric += get_array_size(line, struct[i+1])
            continue
        
        if '[' in line:
            continue

        line = line[:-1]
        line = line.split(' ')
        line_type = line[1]

        if line_type in sizes:
            total_numaric += sizes[line_type]
        elif line_type == 'T':
            total_ts += 1
        else:
            if '<' in line_type:
                sub_type = line_type.split('<')[1][:-1]
                sub_type_size = get_struct_size(sub_type)()
                total_numaric += get_struct_size(line_type.split('<')[0])(sub_type_size)
            else:
                total_numaric += get_struct_size(line_type)()
    
    if has_type:
        f = lambda x: total_numaric + x * total_ts
    else:
        f = lambda: total_numaric
    
    found_names.append(struct_name)
    found_funcs.append(f)

    return f



def get_position(name, in_struct = 'Shared', sub_type = None):
    _, shared = formatted_data[in_struct]
    total = 0
    before_total = -1
    for i, line in enumerate(shared):
        if line.split(' ')[2][:-1] == name:
            before_total = total

        if line.startswith('[MarshalAs'):
            if shared[i+1].split(' ')[2][:-1] == name:
                return shared[i+1].split(' ')[1], (total, total + get_array_size(line, shared[i+1]))
            else:
                total += get_array_size(line, shared[i+1])
        
        if '[' in line:
            continue
        
        line_type = line.split(' ')[1]
        if '<' in line_type:
            sub_type = line_type.split('<')[1][:-1]
            sub_type_size = get_struct_size(sub_type)()
            total += get_struct_size(line_type.split('<')[0])(sub_type_size)
        elif line_type == 'T':
            total += get_struct_size(sub_type)()
        else:
            total += get_struct_size(line_type)()
        
        if before_total != -1:
            return line_type, (before_total, total)



struct_type_dict = {'Single' : 'f', 'Double' : 'd', 'Int32' : 'i', 'Int16' : 'h', 'Int8' : 'b', 'UInt32' : 'I', 'UInt16' : 'H', 'UInt8' : 'B', 'Int64' : 'q', 'UInt64' : 'Q', 'Boolean' : '?', 'Byte' : 'B', 'SByte' : 'b', 'Char' : 'c', 'String' : 's', 'Void' : 'x', 'byte': 'B', 'sbyte': 'b', 'char': 'c', 'string': 's', 'void': 'x'}

data_positions = open('data_positions.json', 'r').read() if os.path.isfile('data_positions.json') else '{}'
data_positions = json.loads(data_positions)

def get_value(data, name, in_struct = 'Shared', sub_type = None, index_in_array = None, array_item_sizes = None, out_s = None):
    global data_positions
    if name in data_positions:
        if type(data_positions[name][0]) == int:
            s, e, poses = data_positions[name]
            val = data[s:e]
            output = dict()
            for val_name, val_type, (ss, se) in poses:
                # if '[' in val_type:
                #     val_type = val_type.split('[')[0]

                if val_type in struct_type_dict:
                    output[val_name] = struct.unpack('<' + str(len(val[ss:se]) // sizes[val_type]) + struct_type_dict[val_type], val[ss:se])[0]
                elif val_type == 'byte[]':
                    unpacked = (val[ss:se].replace(b'\x00', b'')).decode('utf-8')
                    output[val_name] = unpacked
                else:
                    stripped_val_type = val_type
                    if '<' in val_type:
                        stripped_val_type = val_type.split('<')[0]
                    unpacked = get_value(data, val_name, stripped_val_type, sub_type)
                    output[val_name] = unpacked
            
            return output
        else:
            val_type, s, e = data_positions[name]
            val = data[s:e]

            if val_type in struct_type_dict:
                return struct.unpack('<' + str(len(val) // sizes[val_type]) + struct_type_dict[val_type], val)[0]
            elif val_type == 'byte[]':
                return (val.replace(b'\x00', b'')).decode('utf-8')
            else:
                stripped_val_type = val_type
                if '<' in val_type:
                    stripped_val_type = val_type.split('<')[0]
                return get_value(data, name, stripped_val_type, sub_type)



    try:
        val_type, (s, e) = get_position(name, in_struct, sub_type)
    except:
        return
    
    if in_struct != 'Shared' and index_in_array is None:
        s += out_s
        e += out_s
    
    val = data[s:e]
    if val_type == 'T':
        val_type = sub_type

    
    if index_in_array is not None:
        s, e = s + index_in_array * array_item_sizes, e + index_in_array * array_item_sizes
        val = data[s:e]
        
    
    if '[' in val_type and (index_in_array is None or val_type == 'byte[]'):
        val_type = val_type.split('[')[0]
        if val_type == 'byte':
            try:
                val = val.replace(b'\x00', b'').decode('utf-8')
            except:
                pass
            return val
        else:
            output = []
            for i in range(0, len(val) // get_struct_size(val_type)()):
                unpacked = get_value(val, name, in_struct, sub_type, i, (e-s) // (len(val) // get_struct_size(val_type)()), out_s)
                output.append(unpacked)
            return output
    
    if '[' in val_type:
        val_type = val_type.split('[')[0]

    if val_type in struct_type_dict:
        if name not in data_positions and os.path.isfile('data_positions.json') and index_in_array is None:
            with open('data_positions.json', 'r') as f:
                positions = json.load(f)
            with open('data_positions.json', 'w') as f:
                positions[name] = (val_type, s, e)
                data_positions = positions
                json.dump(positions, f)
        
        return struct.unpack('<' + str(len(val) // sizes[val_type]) + struct_type_dict[val_type], val)[0]
    else:
        sub_type = None
        if '<' in val_type:
            stripped_val_type = val_type.split('<')[0]
            _, type_struct = formatted_data[stripped_val_type]
            sub_type = val_type.split('<')[1][:-1]
        elif '[' in val_type:
            stripped_val_type = val_type.split('[')[0]
            _, type_struct = formatted_data[stripped_val_type]
        else:
            stripped_val_type = val_type
            _, type_struct = formatted_data[val_type]
        
        output = dict()
        positions = [s, e, []]
        for line in type_struct:
            if line.startswith('[MarshalAs'):
                continue
            
            line_name = line.split(' ')[2][:-1]
            line_type = line.split(' ')[1]
            if '<' in line_type:
                line_type = line_type.split('<')[0]

            _, (ss, se) = get_position(line_name, stripped_val_type, sub_type)

            if line_type == 'T':
                line_type = sub_type
            
            
            positions[-1].append((line_name, line_type, (ss, se)))

            if line_type in struct_type_dict:
                unpacked = struct.unpack('<' + str(len(val[ss:se]) // sizes[line_type]) + struct_type_dict[line_type], val[ss:se])
                if type(unpacked) == tuple and len(unpacked) == 1:
                    unpacked = unpacked[0]
            else:
                unpacked = get_value(data, line_name, stripped_val_type, sub_type, index_in_array, array_item_sizes, s)
            
            output[line_name] = unpacked
        
        if index_in_array is None:
            if name not in data_positions and os.path.isfile('data_positions.json') and index_in_array is None:
                with open('data_positions.json', 'r') as f:
                    all_positions = json.load(f)
                all_positions[name] = positions
                data_positions = all_positions
                with open('data_positions.json', 'w') as f:
                    json.dump(all_positions, f)
            elif name in data_positions and index_in_array is None:
                with open('data_positions.json', 'w') as f:
                    data_positions = {name: positions}
                    json.dump({name: positions}, f)
        
        return output
    




if __name__ == '__main__':
    raw_data = open('log.txt', 'rb').read()
    print(get_value(raw_data, 'LayoutName'))
    # print(get_struct_size("DriverData")())