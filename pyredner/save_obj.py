import torch
import pyredner

def save_obj(shape,
             filename,
             flip_tex_coords = True):
    with open(filename, 'w') as f:
        vertices = shape.vertices.cpu()
        uvs = shape.uvs.cpu() if shape.uvs is not None else None
        normals = shape.normals.cpu() if shape.normals is not None else None
        for i in range(vertices.shape[0]):
            f.write('v {} {} {}\n'.format(vertices[i, 0], vertices[i, 1], vertices[i, 2]))
        if uvs is not None:
            for i in range(uvs.shape[0]):
                if flip_tex_coords:
                    f.write('vt {} {}\n'.format(uvs[i, 0], 1 - uvs[i, 1]))
                else:
                    f.write('vt {} {}\n'.format(uvs[i, 0], uvs[i, 1]))
        if normals is not None:
            for i in range(normals.shape[0]):
                f.write('vn {} {} {}\n'.format(normals[i, 0], normals[i, 1], normals[i, 2]))
        indices = shape.indices.cpu() + 1
        uv_indices = shape.uv_indices.cpu() + 1 if shape.uv_indices is not None else None
        normal_indices = shape.normal_indices.cpu() + 1 if shape.normal_indices is not None else None
        for i in range(indices.shape[0]):
            vi = (indices[i, 0], indices[i, 1], indices[i, 2])
            if uv_indices is not None:
                uvi = (uv_indices[i, 0], uv_indices[i, 1], uv_indices[i, 2])
            else:
                if uvs is not None:
                    uvi = vi
                else:
                    uvi = ''
            if normal_indices is not None:
                ni = (normal_indices[i, 0], normal_indices[i, 1], normal_indices[i, 2])
            else:
                if normals is not None:
                    ni = vi
                else:
                    ni = ''
            if normals is not None:
                f.write('f {}/{}/{} {}/{}/{} {}/{}/{}\n'.format(\
                    vi[0], uvi[0], ni[0],
                    vi[1], uvi[1], ni[1],
                    vi[2], uvi[2], ni[2]))
            elif uvs is not None:
                f.write('f {}/{} {}/{} {}/{}\n'.format(\
                    vi[0], uvi[0],
                    vi[1], uvi[1],
                    vi[2], uvi[2]))
            else:
                f.write('f {} {} {}\n'.format(\
                    vi[0],
                    vi[1],
                    vi[2]))
