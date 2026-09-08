// Same-binary local checkpoint. No pointers exist in Vertex/Tetra pool objects.
// Nonphysical derived halfedge/triangle caches are reconstructed after loading.
#pragma once
#include "universe.hpp"
#include "simulation.hpp"
#include <fstream>
#include <cstdio>
#include <string>

template<class T> void store_vec(std::ostream& o,const std::vector<T>& v) {
    int n=v.size();o.write((char*)&n,sizeof(n));o.write((char*)v.data(),sizeof(T)*n);
}
template<class T> void load_vec(std::istream& i,std::vector<T>& v) {
    int n;i.read((char*)&n,sizeof(n));if(n<0 || n>10000000) throw std::runtime_error("checkpoint vector size");
    v.resize(n);i.read((char*)v.data(),sizeof(T)*n);
}
inline void save_checkpoint(const std::string& path,int completed) {
    std::ofstream o(path+".pending",std::ios::binary);
    o<<"CDT_CHECKPOINT_V1\n"<<completed<<"\n"<<std::setprecision(17)<<Simulation::k3<<"\n"<<Universe::nSlices<<"\n";
    Simulation::save_rng(o);Universe::save_rng(o);
    Vertex::save_pool(o);Tetra::save_pool(o);
    Universe::verticesAll.save_bag(o);Universe::tetrasAll.save_bag(o);Universe::tetras31.save_bag(o);Universe::verticesSix.save_bag(o);
    store_vec(o,Universe::sliceSizes);store_vec(o,Universe::slabSizes);
    o.flush();if(!o) throw std::runtime_error("checkpoint write failed");o.close();
    if(std::rename((path+".pending").c_str(),path.c_str())!=0) throw std::runtime_error("checkpoint rename failed");
}
inline int load_checkpoint(const std::string& path) {
    std::ifstream i(path,std::ios::binary);std::string magic;std::getline(i,magic);
    if(magic!="CDT_CHECKPOINT_V1") throw std::runtime_error("checkpoint version");
    int completed;i>>completed>>Simulation::k3>>Universe::nSlices;
    Simulation::load_rng(i);Universe::load_rng(i);i.get();
    Vertex::load_pool(i);Tetra::load_pool(i);
    Universe::verticesAll.load_bag(i);Universe::tetrasAll.load_bag(i);Universe::tetras31.load_bag(i);Universe::verticesSix.load_bag(i);
    load_vec(i,Universe::sliceSizes);load_vec(i,Universe::slabSizes);
    if(!i) throw std::runtime_error("checkpoint truncated");
    Universe::strictness=3;Universe::volfix_switch=1;
    Universe::updateGeometry();return completed;
}
